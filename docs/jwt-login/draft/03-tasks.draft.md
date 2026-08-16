# 任务拆分

> 节点 ID: `split_tasks`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:08:00
> 执行状态: 进行中
> 备注: `skip_clarification=true`，决策项按建议默认落定

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

# 任务初稿：用户 JWT 登录认证

> 节点：`split_tasks` · 阶段：初稿  
> 依据：`01-requirements.md`、`02-plan.md`  
> 说明：`skip_clarification=true`，决策项已按建议默认落定，无 pending。

---

## 1. 任务总览（草稿）

| ID | 标题 | 优先级 | 影响模块 | 预估 |
|----|------|--------|----------|------|
| TASK-01 | 领域层：User 聚合、Port、凭证服务与异常 | P0 | auth.domain | 0.5d |
| TASK-02 | 基础设施：JSON 仓储、bcrypt、JWT、配置与预置用户 | P0 | auth.infrastructure | 0.75d |
| TASK-03 | 基础设施：JwtAuthFilter 与公开/受保护路径 | P0 | auth.infrastructure | 0.5d |
| TASK-04 | 应用层：login / me / logout 用例 | P0 | auth.application | 0.5d |
| TASK-05 | 接口层：Controller、DTO、Assembler、全局异常 | P0 | auth.interfaces | 0.5d |
| TASK-06 | 最小静态 UI（登录页 / 受保护首页） | P0 | static + infra 视图映射 | 0.5d |
| TASK-07 | API 自动化测试（成功/失败/鉴权/过期） | P0 | test | 0.5d |
| TASK-08 | E2E + README/启动与已知限制说明 | P0 | docs + e2e | 0.5d |

**建议执行顺序**：TASK-01 → TASK-02 → TASK-03 → TASK-04 → TASK-05 → TASK-06 → TASK-07 → TASK-08。

## 2. 任务详情（草稿摘要）

### TASK-01 领域层
- 包：`com.zeiss.ecp.assistant.auth.domain`
- 产出：User / UserId、UserRepository、PasswordHasher、TokenProvider、CredentialDomainService、领域异常
- 硬约束：无 Spring/JPA/Servlet/jjwt import
- DoD：领域单测覆盖凭证成功/失败统一语义

### TASK-02 基础设施（持久化与出站 Port）
- FileUserRepository（`./data/users.json`）、BcryptPasswordHasher、JwtTokenProvider（HS256）、AuthProperties、UserDataInitializer（testuser）
- DoD：重启后用户仍在；文件无明文密码；密钥/过期可配置

### TASK-03 JwtAuthFilter
- OncePerRequestFilter；Bearer 解析；公开路径放行；受保护 API 401 JSON
- DoD：缺/非法/过期令牌均 401，且不进入业务

### TASK-04 应用层
- AuthApplicationService：login / currentUser / logout
- 只依赖 Port；logout 校验令牌有效即成功

### TASK-05 接口层
- 契约见第 3 节；Controller 仅调 ApplicationService
- GlobalExceptionHandler 映射 401/400

### TASK-06 UI
- `/login`、`/`；localStorage.access_token；调用 login/me/logout

### TASK-07 / TASK-08
- MockMvc 覆盖验收 API 点；Playwright E2E；README 启动与已知限制

## 3. API 详细设计（草稿）

见定稿将展开的完整契约；要点：

| 方法 | 路径 | 访问 |
|------|------|------|
| POST | `/api/auth/login` | 公开 |
| GET | `/api/auth/me` | Bearer |
| POST | `/api/auth/logout` | Bearer |
| GET | `/login` | 公开页面 |
| GET | `/` | 页面侧门禁 |

登录成功：`access_token` / `token_type=Bearer` / `expires_in`  
JWT claims：`sub`、`username`、`iat`、`exp`  
错误：`{error, message}`

## 4. 依赖关系（草稿）

```text
TASK-01 (domain)
    ↓
TASK-02 (infra ports) ──→ TASK-03 (filter)
    ↓                         ↓
TASK-04 (application) ←───────┘
    ↓
TASK-05 (interfaces) → TASK-06 (UI)
    ↓                     ↓
TASK-07 (API tests) ←─────┘
    ↓
TASK-08 (E2E + docs)
```

## 5. 与定制约束符合性（初稿自检）

- 任务按 domain → infrastructure → application → interfaces 排序
- Port 在 domain，实现在 infrastructure
- Controller 不直调仓储；Filter 在 infrastructure
- 预置账号以需求 testuser 为准（覆盖仓库旧演示账号口径）

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
