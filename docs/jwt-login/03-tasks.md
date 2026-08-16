# 任务拆分

> 节点 ID: `split_tasks`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:08:30
> 执行状态: 成功
> 备注: 决策已全部 resolved（skip_clarification）；等待用户定稿确认

---

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: T1
    category: api_contract
    question: "REST JSON 字段命名采用 snake_case 还是 camelCase？"
    why_it_matters: "决定 Login/Me/Error 响应字段名与测试断言；需求验收写的是 access_token / token_type / expires_in。"
    suggestion: "全局 Jackson SNAKE_CASE：对外一律 snake_case（access_token、user_id 等）。"
    status: resolved
    answer: "使用 Spring Jackson property-naming-strategy=SNAKE_CASE；对外 JSON 为 snake_case。"
  - id: T2
    category: api_contract
    question: "GET /api/auth/me 返回哪些用户字段？"
    why_it_matters: "影响 DTO、页面展示与 E2E 断言口径。"
    suggestion: "返回 user_id 与 username，与 JWT sub/username 对齐；不返回密码哈希。"
    status: resolved
    answer: "Me 响应仅含 user_id、username；与令牌身份一致；不含敏感字段。"
  - id: T3
    category: api_contract
    question: "认证失败与校验失败的错误响应体结构如何约定？"
    why_it_matters: "统一客户端与自动化测试断言；避免多套错误格式。"
    suggestion: "统一 {\"error\":\"<code>\",\"message\":\"<文案>\"}；凭证失败 error=invalid_credentials；令牌问题 error=unauthorized；格式问题 400 + bad_request。"
    status: resolved
    answer: "统一 ErrorResponse：error + message。invalid_credentials / unauthorized → 401；bad_request → 400。凭证失败 message 固定为「用户名或密码错误」。"
  - id: T4
    category: api_contract
    question: "登出成功响应体如何约定？"
    why_it_matters: "接口契约需完整；客户端与测试需稳定字段。"
    suggestion: "{\"message\":\"logged_out\"}，HTTP 200。"
    status: resolved
    answer: "POST /api/auth/logout 成功返回 200 + {\"message\":\"logged_out\"}；不做服务端黑名单。"
  - id: T5
    category: architecture
    question: "URL /login 如何映射到静态 login.html？"
    why_it_matters: "E2e base 与验收要求打开 /login；Spring 默认只暴露 /login.html。"
    suggestion: "infrastructure 中 ViewController forward:/login.html；页面侧门禁不由 Filter 强制（静态路径放行）。"
    status: resolved
    answer: "AuthInfrastructureConfig 注册 /login → forward:/login.html；/ 使用 index.html；受保护页由前端 localStorage 门禁，API 由 JwtAuthFilter 鉴权。"
  - id: T6
    category: data
    question: "仓库若已有演示账号 admin，是否必须改为需求定稿的 testuser？"
    why_it_matters: "计划风险项已指出须与需求统一；影响初始化、文档、API/E2E。"
    suggestion: "以需求为准统一为 testuser / Test@123456；实现与测试同步修改。"
    status: resolved
    answer: "预置账号必须以 testuser / Test@123456 为准（哈希落盘）；文档与全部自动化测试同步；不得继续以 admin/password123 作为验收口径。"
  - id: T7
    category: task_scope
    question: "任务粒度按四层拆分还是按垂直切片（每个 API 一条）？"
    why_it_matters: "影响 implement 执行顺序与并行度；定制约束要求 domain → infrastructure → application → interfaces。"
    suggestion: "按层拆主任务，API 详细设计独立成章供接口任务引用；测试单独任务。"
    status: resolved
    answer: "按 DDD 层拆分主任务并标明依赖；API 契约集中在「API 详细设计」；UI、API 测试、E2E、文档分任务收口。"
  - id: T8
    category: testing
    question: "浏览器 E2E 落在何处、用什么工具？"
    why_it_matters: "验收标准要求登录→看信息→登出全流程；workflow e2e.base_url=http://localhost:8080。"
    suggestion: "verify_tests 用 Playwright（或 MCP）对运行中的 8080 服务做 E2E；本节点只规定场景与选择器约定。"
    status: resolved
    answer: "E2E 使用 Playwright（或等价）对 http://localhost:8080；场景：/login → testuser 登录 → / 展示 me → 登出 → 再访 / 须回登录页。API 自动化用 MockMvc/集成测试。"
```

```yaml tasks_approval
status: approved
confirmed_at: "2026-08-16T15:08:00+08:00"
user_note: "确认"
```

# 任务定稿：用户 JWT 登录认证

> 节点 ID: `split_tasks`  
> 需求类型: `new`  
> 依据文档: `01-requirements.md`、`02-plan.md`  
> 决策来源: 初稿清单已全部 resolved（本节点 `skip_clarification=true`，按建议默认落定）

---

## 1. 任务总览表

| ID | 标题 | 优先级 | 影响模块 | 预估工时 |
|----|------|--------|----------|----------|
| TASK-01 | 领域层：User 聚合、Port、凭证领域服务与异常 | P0 | `auth.domain` | 0.5d |
| TASK-02 | 基础设施：JSON 用户仓储、bcrypt、JWT、配置与预置用户 | P0 | `auth.infrastructure` | 0.75d |
| TASK-03 | 基础设施：JwtAuthFilter（公开/受保护路径与 401） | P0 | `auth.infrastructure` | 0.5d |
| TASK-04 | 应用层：login / me / logout 用例编排 | P0 | `auth.application` | 0.5d |
| TASK-05 | 接口层：AuthController、DTO、Assembler、全局异常 | P0 | `auth.interfaces` | 0.5d |
| TASK-06 | 最小静态 UI：登录页、受保护首页、localStorage | P0 | `static` + infra 视图映射 | 0.5d |
| TASK-07 | API 自动化测试（登录/鉴权/过期/存储断言） | P0 | `src/test` | 0.5d |
| TASK-08 | 浏览器 E2E + README 启动与已知限制 | P0 | docs + e2e | 0.5d |

包根：`com.zeiss.ecp.assistant.auth`（工程根 `pom.xml`，Java 17 + Spring Boot 3.3）。

---

## 2. 任务详情

### TASK-01 — 领域层骨架与凭证规则

| 项 | 内容 |
|----|------|
| **目标** | 建立 auth 领域模型、Port 与统一凭证失败语义，供外层依赖倒置 |
| **输入** | 需求 §7.1、计划 §3.1、决策 T6/T7 |
| **输出** | User 聚合根、UserId；`UserRepository` / `PasswordHasher` / `TokenProvider` Port；`CredentialDomainService`；`InvalidCredentialsException` / `InvalidTokenException` / `UnauthorizedException`；领域单元测试 |
| **涉及路径** | `src/main/java/.../auth/domain/**`；`src/test/java/.../auth/domain/**` |
| **依赖** | 无（首任务） |
| **DoD** | ① 四层中 domain 无 Spring/JPA/Servlet/jjwt 等 outward 依赖；② 密码校验失败统一抛 InvalidCredentials，不暴露用户是否存在；③ TokenProvider 接口含签发与解析校验（claims：sub/userId、username、iat、exp 语义）；④ 领域单测覆盖成功认证与错误密码 |

### TASK-02 — 基础设施：仓储、哈希、JWT、配置、初始化

| 项 | 内容 |
|----|------|
| **目标** | 实现 domain Port；本地 JSON 持久化；预置 testuser；可配置密钥与过期 |
| **输入** | TASK-01 Port；计划 §2/§5；决策 T6 |
| **输出** | `FileUserRepository`、`UserFileRecord`、`BcryptPasswordHasher`、`JwtTokenProvider`（jjwt HS256）、`AuthProperties`、`UserDataInitializer`、`AuthInfrastructureConfig`（Bean 绑定）、`application.yml` / `application-local.yml.example` |
| **涉及路径** | `.../infrastructure/persistence/**`、`.../infrastructure/security/{BcryptPasswordHasher,JwtTokenProvider}.java`、`.../infrastructure/config/**`、`src/main/resources/application.yml`、仓库根 example 配置 |
| **依赖** | TASK-01 |
| **DoD** | ① 默认用户文件 `./data/users.json`（可配置）；② 预置 **testuser**，密码 **Test@123456** 仅以 bcrypt 哈希写入；③ `auth.jwt.secret` / `AUTH_JWT_SECRET`、`auth.jwt.expiration-seconds` 默认 7200；④ 真实密钥不入库；⑤ PO/文件模型不泄漏到 application/interfaces |

### TASK-03 — 基础设施：JwtAuthFilter

| 项 | 内容 |
|----|------|
| **目标** | 对受保护 API 校验 Bearer JWT；公开路径与静态资源放行；失败写 401 JSON |
| **输入** | TASK-02 TokenProvider；决策 T3/T5 |
| **输出** | `JwtAuthFilter`（`OncePerRequestFilter`）注册到过滤器链；身份属性（userId/username）写入 request，供 me/logout |
| **涉及路径** | `.../infrastructure/security/JwtAuthFilter.java`、过滤器注册配置 |
| **依赖** | TASK-02 |
| **DoD** | ① 不引入完整 `spring-boot-starter-security`；② `POST /api/auth/login`、静态资源、非 `/api/**` 页面路径放行；③ `/api/auth/me`、`/api/auth/logout` 缺令牌/非法/过期 → 401，body 符合 §3.5；④ Filter 内不写核心业务规则 |

### TASK-04 — 应用层用例

| 项 | 内容 |
|----|------|
| **目标** | 编排登录签发、当前用户、登出确认三类用例 |
| **输入** | TASK-01/02 Port；需求 §7.2 |
| **输出** | `AuthApplicationService`（或等价）；应用出参如 `AccessTokenResult`、`CurrentUserView` |
| **涉及路径** | `.../application/service/**`、`.../application/dto/**`（可选 command） |
| **依赖** | TASK-01；运行依赖 TASK-02 实现 |
| **DoD** | ① `login`：按用户名加载 → CredentialDomainService 校验 → TokenProvider 签发 → 返回 accessToken、tokenType=`Bearer`、expiresIn；② `currentUser`：基于有效令牌返回 userId+username；③ `logout`：确认令牌有效后成功返回（无黑名单）；④ 禁止 import infrastructure 具体类 |

### TASK-05 — 接口层 REST（引用 §3）

| 项 | 内容 |
|----|------|
| **目标** | 暴露 §3 约定的三个 API；DTO 与领域分离；统一异常映射 |
| **输入** | TASK-04；**API 详细设计 §3.1–§3.5**；决策 T1–T4 |
| **输出** | `AuthController`、`LoginRequest`/`LoginResponse`/`MeResponse`/`LogoutResponse`/`ErrorResponse`、`AuthAssembler`、`GlobalExceptionHandler` |
| **涉及路径** | `.../interfaces/rest/**`、`.../interfaces/assembler/**`、`.../interfaces/exception/**` |
| **依赖** | TASK-04（及 TASK-03 保证受保护路径） |
| **DoD** | ① Controller 仅调 ApplicationService；② Bean Validation 仅格式校验；③ JSON snake_case；④ 契约与 §3 一致；⑤ 错误不泄露用户是否存在 |

### TASK-06 — 最小 Web UI

| 项 | 内容 |
|----|------|
| **目标** | 同源静态登录与受保护首页，满足页面侧验收 |
| **输入** | §3 API；决策 T5/T6；需求 §7.5 |
| **输出** | `static/login.html`、`static/index.html`、`static/js/auth.js`；`/login` forward 配置 |
| **涉及路径** | `src/main/resources/static/**`；infra `addViewControllers` |
| **依赖** | TASK-05 |
| **DoD** | ① `/login` 可打开并提交；② 成功将 `access_token` 写入 localStorage，进入 `/`；③ `/` 带 Bearer 调 `/api/auth/me` 展示 user_id/username；④ 错误密码统一提示且不进入受保护区；⑤ 无 token 访问 `/` → 引导 `/login`；⑥ 登出调 API、清 localStorage、回登录页；⑦ 页面文案中的预置账号为 testuser |

### TASK-07 — API 自动化测试

| 项 | 内容 |
|----|------|
| **目标** | 覆盖需求验收 API 项 1–6 |
| **输入** | §3；TASK-01–05 |
| **输出** | 领域单测（若未在 TASK-01 完成则补齐）+ MockMvc/SpringBoot 集成测试 |
| **涉及路径** | `src/test/java/.../auth/**`、`src/test/resources/application.yml` |
| **依赖** | TASK-05 |
| **DoD** | ① 正确登录返回三要素；② 错误密码 401 且无 token；③ 有效 token 访问 me；④ 缺/非法/过期 token → 401；⑤ payload 含 sub、username、iat、exp，过期策略符合配置；⑥ users 文件无明文密码；⑦ 全部使用 **testuser / Test@123456** |

### TASK-08 — E2E 与文档

| 项 | 内容 |
|----|------|
| **目标** | 浏览器全流程验收 + 本地启动说明 |
| **输入** | TASK-06/07；决策 T8；需求验收 7–11 |
| **输出** | Playwright（或等价）E2E 场景说明/脚本；根 `README.md` 更新 |
| **涉及路径** | 仓库根 `README.md`；E2E 资产（按 verify 节点约定） |
| **依赖** | TASK-06、TASK-07 |
| **DoD** | ① base_url `http://localhost:8080`；② 登录→看信息→登出→再访受保护页需登录；③ README：启动、`AUTH_JWT_SECRET`、测试账号、已知限制（登出无服务端立即失效）；④ 架构自检清单可勾选 |

---

## 3. API 详细设计

> 全局：`Content-Type: application/json`；Jackson **SNAKE_CASE**；默认基址 `http://localhost:8080`。

### 3.1 POST `/api/auth/login`（公开）

**用途**：校验用户名密码，签发 access_token。

**请求**

```json
{
  "username": "testuser",
  "password": "Test@123456"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 非空 |
| password | string | 是 | 非空 |

**成功响应** `200 OK`

```json
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 7200
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| access_token | string | JWT 字符串 |
| token_type | string | 固定 `Bearer` |
| expires_in | number | 秒；默认与 `auth.jwt.expiration-seconds` 一致（7200） |

**JWT payload（HS256）**

| Claim | 说明 |
|-------|------|
| sub | 用户 id（与 Me.user_id 一致） |
| username | 用户名 |
| iat | 签发时间 |
| exp | 过期时间 |

**错误**

| 场景 | HTTP | error | message |
|------|------|-------|---------|
| 用户名或密码错误（含用户不存在，统一文案） | 401 | `invalid_credentials` | `用户名或密码错误` |
| JSON 缺失/字段格式非法 | 400 | `bad_request` | 校验或解析说明 |

**鉴权**：无。引用任务：TASK-05（实现）、TASK-07（测试）。

---

### 3.2 GET `/api/auth/me`（受保护）

**用途**：返回当前令牌对应用户基本信息。

**请求头**

```http
Authorization: Bearer <access_token>
```

**成功响应** `200 OK`

```json
{
  "user_id": "<uuid-or-id>",
  "username": "testuser"
}
```

**错误**

| 场景 | HTTP | error | message |
|------|------|-------|---------|
| 缺少/非 Bearer/空 token | 401 | `unauthorized` | `未认证或令牌无效` |
| 非法签名或篡改 | 401 | `unauthorized` | `未认证或令牌无效` |
| 过期 token | 401 | `unauthorized` | `未认证或令牌无效` |

**鉴权**：JwtAuthFilter + 应用层令牌校验。引用：TASK-03、TASK-05、TASK-07。

---

### 3.3 POST `/api/auth/logout`（受保护）

**用途**：确认当前令牌有效后返回成功；**不**做服务端黑名单。客户端须清除 localStorage。

**请求头**

```http
Authorization: Bearer <access_token>
```

**请求体**：无（可空 body）。

**成功响应** `200 OK`

```json
{
  "message": "logged_out"
}
```

**错误**：同 §3.2（401 unauthorized）。

**已知限制**：登出后未过期的 access_token 在 API 侧仍可能被接受；页面侧验收以清除本地令牌为准。引用：TASK-05、TASK-06、TASK-08。

---

### 3.4 页面路由（同源静态）

| 方法 | 路径 | 访问 | 行为 |
|------|------|------|------|
| GET | `/login` | 公开 | forward → `/login.html` |
| GET | `/` | 页面侧门禁 | `index.html`；无 token 时前端重定向 `/login` |
| GET | `/login.html`、`/index.html`、`/js/**` | 公开静态 | 静态资源 |

页面不依赖服务端 Session；API 鉴权与页面门禁双轨。

---

### 3.5 统一错误体

```json
{
  "error": "<code>",
  "message": "<human readable>"
}
```

| error | HTTP | 使用场景 |
|-------|------|----------|
| `invalid_credentials` | 401 | 登录凭证失败 |
| `unauthorized` | 401 | 令牌缺失/非法/过期 |
| `bad_request` | 400 | 请求体/校验失败 |

Filter 直接写回的 401 须与上述字段一致，避免两套格式。

---

## 4. 依赖关系与建议执行顺序

```text
TASK-01 domain
    │
    ▼
TASK-02 infra（仓储/哈希/JWT/配置/预置用户）
    │
    ├──────────────────┐
    ▼                  ▼
TASK-04 application   TASK-03 JwtAuthFilter
    │                  │
    └────────┬─────────┘
             ▼
        TASK-05 interfaces（§3 API）
             │
             ▼
        TASK-06 静态 UI
             │
             ▼
        TASK-07 API 测试
             │
             ▼
        TASK-08 E2E + README
```

**建议执行顺序（串行）**：  
`TASK-01 → TASK-02 → TASK-03 → TASK-04 → TASK-05 → TASK-06 → TASK-07 → TASK-08`

说明：TASK-03 与 TASK-04 在 TASK-02 完成后理论上可并行，但为降低联调成本，推荐仍按上序串行；若并行，须在 TASK-05 前两者均完成。

---

## 5. 与定制约束符合性说明

| 自检项 | 任务侧落实 |
|--------|------------|
| 四层包结构 | TASK-01–05 分属 domain / infrastructure / application / interfaces |
| domain 无 outward 依赖 | TASK-01 DoD |
| Repository / JWT / Hasher Port 在 domain，实现在 infrastructure | TASK-01/02 |
| Controller 仅依赖 ApplicationService | TASK-05 DoD |
| 核心凭证规则在领域层 | CredentialDomainService（TASK-01） |
| 出站 JWT/哈希走 DIP | TASK-02 |
| 入站 Filter 在 infrastructure | TASK-03 |
| 依赖顺序 domain → infra → application → interfaces | §4 |

若实现阶段发现与本节冲突，须显式提出决策，不得静默违反。

---

## 6. 实现时特别注意（存量对齐）

仓库根工程可能已存在以 `admin` / `password123` 为演示账号的实现与测试。**本期验收与文档一律以 `testuser` / `Test@123456` 为准**（决策 T6）。implement 节点须同步修正初始化器、静态页提示、README、单元/集成测试中的账号口径，避免双轨。

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | split_tasks |
| status | completed |
| next_node | implement_code |
| phase | tasks |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T15:08:33 |
