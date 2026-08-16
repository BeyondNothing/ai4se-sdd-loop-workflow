# 需求分析与澄清

> 节点 ID: `analyze_requirements`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:02:58
> 执行状态: 成功
> 备注: 节点产出已完成，已自动退出 CLI

---

```yaml requirement_metadata
requirement_type: new
requirement_summary: "新增 auth 限界上下文：JWT 登录签发、请求鉴权、最小登录/受保护页与 E2E 验收"
judgment_basis: "仓库尚无统一用户认证能力，本次从零建设登录、令牌、受保护资源与最小 Web UI"
change_scope: "新建 auth 四层模块（domain/application/interfaces/infrastructure）、静态登录与受保护页、配置项、API 与 E2E 测试"
affected_modules:
  - "auth.domain"
  - "auth.application"
  - "auth.interfaces"
  - "auth.infrastructure"
compatibility_risk: low
needs_clarification: false
open_questions_count: 0
```

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: Q1
    category: scope
    question: "用户数据采用何种本地存储方式（内存 / 文件 / 数据库）？"
    why_it_matters: "影响基础设施层仓储实现选型、启动依赖与验收环境准备。"
    suggestion: "采用本地文件持久化（如 JSON/SQLite 文件），进程重启后测试用户仍可用；预置 1 个测试账号。"
    status: resolved
    answer: "采用本地文件持久化；预置至少 1 个测试用户。不引入外部独立数据库服务。"
  - id: Q2
    category: security
    question: "登出是否必须实现服务端令牌立即失效（黑名单/版本号）？"
    why_it_matters: "决定验收口径：登出后旧 JWT 是否仍可调用受保护 API。"
    suggestion: "本期不做黑名单；登出校验当前令牌有效后返回成功，客户端清除本地令牌。受保护页面须因本地无令牌而无法继续访问；API 侧旧令牌在过期前仍可能有效（已知限制，文档化）。"
    status: resolved
    answer: "本期不实现服务端黑名单/令牌版本号。登出：校验当前令牌有效并返回成功；客户端清除本地令牌。页面侧登出后不可继续访问受保护区域；API 侧旧 access_token 在过期前仍可能有效，作为已知限制记录，不阻塞本期验收。"
  - id: Q3
    category: scope
    question: "前端令牌存放位置选用 localStorage 还是 Cookie？"
    why_it_matters: "影响前端实现说明、XSS/CSRF 权衡及 E2E 断言方式。"
    suggestion: "使用 localStorage 存 access_token；请求头携带 Authorization: Bearer <token>。"
    status: resolved
    answer: "使用 localStorage 保存 access_token；后续请求通过 Authorization: Bearer 头携带。实现文档中说明该选择。"
  - id: Q4
    category: compatibility
    question: "登录页与 API 是否由同一后端进程提供（同源）？"
    why_it_matters: "影响 CORS、部署与本地启动方式；workflow e2e.base_url 为 http://localhost:8080。"
    suggestion: "同一服务同源提供静态登录/受保护页与 /api/auth/*；默认监听 8080（可配置）。"
    status: resolved
    answer: "同一后端进程同源提供最小 Web UI（/login、受保护首页）与认证 API；默认端口 8080，可通过环境变量配置。"
  - id: Q5
    category: data
    question: "预置测试用户的账号与密码约定是什么？"
    why_it_matters: "联调、自动化测试与 E2E 需要稳定凭证。"
    suggestion: "username=testuser，password=Test@123456；仅用于本地/测试，密码哈希存储。"
    status: resolved
    answer: "预置测试用户 username=testuser，password=Test@123456；密码以单向哈希存储，明文仅出现在文档/测试配置说明中，不写入持久化明文与运行日志。"
  - id: Q6
    category: architecture
    question: "认证能力是否作为独立限界上下文（auth）按 DDD 四层落地？"
    why_it_matters: "项目定制约束要求需求/计划/实现按四层描述与拆分。"
    suggestion: "新建 auth 限界上下文，包结构按 interfaces / application / domain / infrastructure 划分。"
    status: resolved
    answer: "作为独立 auth 限界上下文新建；严格按 DDD 四层：interfaces（REST/页面入口适配）→ application（登录/登出/当前用户用例）→ domain（用户聚合、凭证校验、JWT 相关领域规则与 Port）→ infrastructure（用户仓储实现、JWT 签发校验适配、配置）。禁止 Controller 直调仓储或跨层违规依赖。"
```

```yaml requirement_approval
status: approved
confirmed_at: "2026-08-16T15:02:00+08:00"
user_note: "确认"
```

# 需求定稿：用户 JWT 登录认证

## 1. 需求判断

| 项 | 结论 |
|----|------|
| 需求类型 | **新需求** |
| 判断依据 | 系统尚无统一身份认证；本次从零新增 JWT 登录、鉴权过滤器、受保护接口示例与最小 Web UI |
| 变更范围 | 新建 `auth` 限界上下文（DDD 四层）+ 静态登录/受保护页 + 配置与测试 |
| 兼容性风险 | **低**（无既有认证 API/会话契约需兼容） |
| 待澄清 | 无（已跳过交互澄清，默认结论见「澄清结论」） |

## 2. 澄清结论

| ID | 结论 |
|----|------|
| Q1 | 本地**文件**持久化用户；预置测试用户；不引入外部 DB 服务 |
| Q2 | **不做**服务端黑名单；登出校验令牌并成功返回；客户端清 token；页面侧须重新登录；API 侧旧 token 过期前可能仍有效（已知限制） |
| Q3 | 令牌存 **localStorage**，请求用 `Authorization: Bearer` |
| Q4 | **同源同进程**提供 UI 与 API；默认端口 **8080**（可配置） |
| Q5 | 测试账号 **testuser / Test@123456**（哈希存储） |
| Q6 | 独立 **auth** 限界上下文，严格 **DDD 四层** 与依赖方向 |

## 3. 背景与目标

### 背景

系统缺少统一的用户身份认证能力。需要新增基于 JWT 的登录认证模块，使客户端在用户名密码校验通过后获得访问令牌，并在后续请求中携带令牌访问受保护资源。

### 目标

实现可落地的 JWT 登录能力，覆盖：

1. 登录签发 access_token
2. 令牌校验与受保护资源访问
3. 基础登出约定（无服务端立即失效）
4. 最小登录页 + 受保护页
5. API 自动化测试与浏览器 E2E 全流程验收

## 4. 现状与差距

- 无 auth 限界上下文与用户凭证模型
- 无登录/鉴权/当前用户等用例与 REST 暴露
- 无登录页及端到端联调路径
- 需按 DDD 四层新建，依赖方向：interfaces → application → domain ← infrastructure

## 5. 范围

### 5.1 本次包含

- 登录签发 JWT（`POST /api/auth/login`）
- JWT 约定：HS256、可配置密钥与过期；payload 含 `sub`、`username`、`iat`、`exp`；默认有效期 2 小时
- 请求鉴权（过滤器/拦截器）与示例受保护接口 `GET /api/auth/me`
- 基础登出 `POST /api/auth/logout`（校验当前令牌有效 + 成功响应）
- 本地文件用户存储 + 预置测试用户
- 最小 Web UI：`/login`、受保护首页、登出入口
- 可配置项、单元/接口测试、浏览器 E2E（打开登录页 → 登录 → 查看用户信息 → 登出）
- 清晰本地启动说明（默认 `http://localhost:8080`）

### 5.2 本次不包含

- 用户注册 / 邮箱验证 / 找回密码
- Refresh Token
- RBAC 细粒度权限、多租户
- 服务端令牌黑名单 / 令牌版本号立即失效
- 复杂前端工程（多页 SPA、设计系统）

## 6. 角色与用户场景

| 角色 | 目标 | 主路径 |
|------|------|--------|
| 终端用户 | 登录后查看本人信息并登出 | `/login` → 提交凭证 → 受保护页展示 `/api/auth/me` → 登出回登录页 |
| API 调用方 | 获取 Bearer 令牌访问受保护 API | `POST /login` → `Authorization` 访问 `/me` |
| 开发/测试 | 稳定验收 | 预置账号 + API 测试 + E2E |

### 关键场景

- 错误密码：API 返回 401；页面统一提示「用户名或密码错误」，不进入受保护区
- 未登录访问受保护页：引导至 `/login`
- 令牌缺失/非法/过期访问受保护 API：401
- 登出后：本地令牌清除，页面不可继续访问受保护区（须重新登录）

## 7. 功能需求（按 DDD 四层）

> 需求层只描述能力与归属；类名、框架选型、详细 API schema 由 plan/implement 节点展开。下列路径/字段为验收口径约定，非接口详细设计。

### 7.1 领域层（domain）

- **用户聚合**：用户唯一标识、用户名、密码哈希等；对外仅通过聚合/领域行为维护一致性
- **凭证规则**：密码不以明文保存；校验失败语义统一（不暴露用户是否存在）
- **Port（接口定义在本层或应用层，实现在基础设施）**：
  - 用户仓储（按聚合根加载/保存）
  - JWT/令牌出站能力（签发、解析校验）——HTTP/JWT 库细节不得进入 domain
- **领域异常**：无效凭证、无效或过期令牌等，供上层映射为 HTTP 401

### 7.2 应用层（application）

- 用例编排（各一 public 用例方法即可）：
  - **登录**：按用户名加载用户 → 校验密码 → 签发 access_token → 返回 token_type=`Bearer` 与 expires_in
  - **当前用户**：基于已解析的身份返回基本信息
  - **登出**：确认当前令牌有效 → 返回成功（不做服务端黑名单）
- 事务边界放在本层；只依赖 domain Port，不依赖 infrastructure 具体类
- 核心不变式留在领域对象/领域服务，避免上帝 ApplicationService

### 7.3 接口层（interfaces）

- REST 适配：`POST /api/auth/login`、`POST /api/auth/logout`、`GET /api/auth/me`
- 登录请求体约定：`username`、`password`；成功响应约定含 `access_token`、`token_type`、`expires_in`
- Request/Response DTO 与领域模型分离；Controller 只做校验格式 → 调 ApplicationService → 组装响应
- 统一异常处理映射业务失败为 401；错误文案不泄露用户是否存在
- 禁止 Controller 直接操作 Entity / Repository

### 7.4 基础设施层（infrastructure）

- 实现用户仓储（本地文件）与 JWT Port（HS256；密钥与过期来自配置/环境变量，禁止硬编码入库）
- 鉴权过滤器/拦截器：解析 `Authorization: Bearer <token>`，无效则 401；通过后进入应用用例
- 预置/初始化测试用户（密码哈希写入文件存储）
- 同源托管静态登录页与受保护页（或等价静态资源适配）
- 框架配置与 Bean 装配；PO/文件模型与领域对象互转留在本层

### 7.5 最小 Web UI

- `/login`：用户名、密码输入与提交；调用登录 API
- 成功：token 写入 **localStorage**，进入受保护页（如 `/` 或 `/home`）
- 受保护页：调用 `/api/auth/me` 展示与 API 一致的用户基本信息；提供登出
- 登出：调用登出 API，清除 localStorage 中的令牌，回到登录页
- 错误密码：页面统一错误提示；不进入受保护区
- 未登录访问受保护页：引导登录页

## 8. 非功能需求

| 类别 | 要求 |
|------|------|
| 安全 | 密码单向哈希（如 bcrypt）；JWT 密钥可配置；日志与持久化无明文密码；统一错误提示 |
| 可配置 | 密钥、access token 过期时间、监听端口等可通过环境变量或配置文件注入 |
| 可测试 | 覆盖登录成功/失败、鉴权成功/失败、过期令牌；浏览器 E2E 全流程 |
| 可运行 | 依赖明确、本地可启动；默认访问 `http://localhost:8080` |
| 架构合规 | 四层包结构清晰；domain 无 outward 依赖；仓储/出站 Port 在 domain（或 application）定义、infrastructure 实现；Controller 仅依赖 ApplicationService |

## 9. 变更影响分析

| 影响面 | 说明 |
|--------|------|
| 新增模块 | auth 四层全套（无既有模块替换） |
| 配置 | 新增 JWT 密钥、过期、端口等；密钥不得提交明文密钥到仓库 |
| 数据 | 本地用户文件及预置测试用户初始化 |
| 兼容性 | 低；无旧认证接口需双轨 |
| 测试 | 新增领域单测、应用/接口测试、E2E |

## 10. 验收标准

### API

1. 正确用户名密码登录，返回有效 JWT（含 `access_token`、`token_type=Bearer`、`expires_in`）
2. 错误密码登录返回 `401`，且不返回令牌
3. 携带有效 JWT 访问 `/api/auth/me`，返回对应用户基本信息
4. 不带令牌、非法令牌、过期令牌访问受保护接口，均返回 `401`
5. JWT payload 含 `sub`、`username`、`iat`、`exp`，且 `exp` 符合配置有效期（默认 2 小时）
6. 密码不以明文出现在存储与运行日志中

### 登录页面 / E2E

7. 浏览器打开登录页，使用 `testuser` / `Test@123456` 登录成功并进入受保护页
8. 登录后页面展示的用户信息与 `/api/auth/me` 一致
9. 错误密码时页面显示统一错误提示且不进入受保护区
10. 登出后清除本地令牌，无法继续访问受保护页面（需重新登录）
11. 相关自动化测试通过（含 API；E2E 可用 Playwright 或等价方式）

### 架构自检（实现阶段对照）

- 四层放置正确；domain 无 Spring/JPA/Web 等基础设施依赖
- Repository / JWT Port 接口在内层，实现在 infrastructure
- Controller 仅调用 ApplicationService
- 核心凭证规则可在领域模型或领域服务中定位

## 11. 已知限制与后续可选

- 登出后，未过期的 access_token 在 API 侧仍可能被接受（无黑名单）；页面侧通过清除本地令牌满足本期验收
- Refresh Token、注册找回、RBAC、服务端立即失效可作为后续迭代

## 12. 与定制约束的符合性说明

本需求按 **DDD 四层** 描述模块与职责：用例在应用层，核心规则与 Port 在领域层，REST/DTO 在接口层，文件仓储与 JWT 适配在基础设施层；依赖仅外→内，出站 JWT 能力走 DIP。后续 plan / tasks / implement / test 须继续遵守同一规范，冲突须显式提出、不得静默违反。
```

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | analyze_requirements |
| status | completed |
| next_node | create_plan |
| phase | requirements |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T15:02:58 |
