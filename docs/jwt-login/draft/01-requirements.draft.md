# 需求分析与澄清

> 节点 ID: `analyze_requirements`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:02:58
> 执行状态: 成功
> 备注: 节点产出已完成，已自动退出 CLI

---

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

# 需求分析初稿：用户 JWT 登录认证

> 状态：初稿（已跳过交互澄清；清单项按建议默认值全部 resolved）

## 1. 需求判断

| 项 | 结论 |
|----|------|
| 需求类型 | **新需求** |
| 判断依据 | 当前仓库无 auth 认证模块/受保护资源能力；本次从零新增 JWT 登录、鉴权与最小 Web UI |
| 变更范围 | 新增 auth 限界上下文（后端四层 + 最小前端页面）及配套配置、测试、本地启动说明 |
| 兼容性风险 | **低**（无既有认证契约需兼容） |

## 2. 背景与目标

### 背景

系统缺少统一用户身份认证。需要基于 JWT 的登录认证，使客户端在用户名密码校验通过后获得访问令牌，并在后续请求中携带令牌访问受保护资源。

### 目标

落地一套可运行的 JWT 登录能力，覆盖：

- 登录签发与令牌约定
- 请求鉴权与受保护资源示例
- 基础登出约定（无服务端黑名单）
- 最小可用登录页 / 受保护页
- API 测试 + 浏览器 E2E 验收

## 3. 现状与差距

- 无统一登录、JWT 签发/校验、受保护 API 示例
- 无登录页与端到端认证联调路径
- 需按 DDD 四层新建 auth 模块，而非在既有模块上打补丁

## 4. 范围

### 本次包含

- `POST /api/auth/login`：校验凭证并签发 access_token
- JWT 约定（HS256、payload 字段、可配置过期与密钥）
- 鉴权过滤器/中间件 + `GET /api/auth/me`
- `POST /api/auth/logout`（校验令牌 + 成功响应；无黑名单）
- 本地文件用户存储 + 预置测试用户
- `/login` 与受保护首页（最小 UI）
- 配置项、单元/接口测试、浏览器 E2E

### 本次不包含

- 用户注册 / 邮箱验证 / 找回密码
- Refresh Token
- RBAC、多租户
- 服务端令牌黑名单 / 令牌版本号立即失效
- 复杂 SPA / 设计系统

## 5. 角色与场景

| 角色 | 场景 |
|------|------|
| 终端用户 | 打开登录页 → 输入账号密码 → 进入受保护页查看本人信息 → 登出 |
| 客户端/联调方 | 调用登录 API 获取 Bearer token，访问受保护 API |
| 开发/测试 | 使用预置账号与自动化测试验证 API 与 E2E |

## 6. 功能需求（按 DDD 分层归属）

### 6.1 领域层（domain）

- 用户聚合：用户标识、用户名、密码哈希等；封装凭证校验相关不变量
- 认证相关领域规则：密码不得明文；校验失败统一语义（不区分用户是否存在）
- Port：用户仓储接口；JWT 签发/解析出站能力接口（或等价 TokenService Port）
- 领域异常：无效凭证、无效/过期令牌等，由上层映射 HTTP 状态

### 6.2 应用层（application）

- 用例：`login`、`logout`、`getCurrentUser`（命名以实现为准）
- 事务/编排边界在本层；通过 Port 加载用户、校验、签发令牌
- 不承载基础设施细节（文件 IO、JWT 库调用细节）

### 6.3 接口层（interfaces）

- REST：登录 / 登出 / 当前用户；入参出参 DTO；薄 Controller
- 页面路由入口（若由同进程提供静态页，可放本层或约定由基础设施静态资源适配，但业务编排仍走应用层）
- 统一错误提示文案：「用户名或密码错误」；鉴权失败 `401`

### 6.4 基础设施层（infrastructure）

- 用户仓储实现（本地文件）
- JWT HS256 签发与校验实现（密钥、过期来自配置）
- 鉴权过滤器/拦截器：解析 `Authorization: Bearer`，失败返回 401
- 配置装配；预置测试用户初始化
- 静态资源托管（登录页、受保护页）若由本服务提供

### 6.5 Web UI（最小）

- `/login`：用户名、密码、提交；失败统一错误提示
- 成功后 localStorage 存 token，进入受保护页
- 受保护页调用 `/api/auth/me` 展示用户信息；提供登出
- 未登录访问受保护页 → 引导至 `/login`

## 7. 非功能需求

- **安全**：bcrypt（或同等）哈希；密钥可配置且不入库；日志/存储无明文密码
- **可配置**：JWT 密钥、过期秒数、监听端口等环境变量/配置文件
- **可测试**：登录成功/失败、鉴权成功/失败、过期令牌；E2E 全流程
- **可运行**：文档化本地启动；默认 `http://localhost:8080`

## 8. 变更影响

| 模块 | 影响 |
|------|------|
| auth.domain | 新增用户模型、仓储 Port、令牌相关 Port/规则 |
| auth.application | 新增登录/登出/当前用户用例 |
| auth.interfaces | 新增 REST 与页面入口 |
| auth.infrastructure | 文件仓储、JWT 适配、过滤器、配置、静态页 |
| 运维/配置 | 新增密钥与过期等配置项 |

## 9. 验收标准（摘要）

API：正确登录得 JWT；错误密码 401 无令牌；有效令牌可访问 `/me`；缺失/非法/过期令牌 401；payload 含 sub/username/iat/exp；密码不明文。

UI/E2E：预置账号可登录并见用户信息；错误密码有提示且不进入受保护区；登出后页面侧需重新登录；自动化测试通过。

## 10. 假设与已知限制

- 跳过交互澄清，上述 Q1–Q6 按建议默认生效
- 登出后旧 JWT 在过期前 API 仍可能有效（无黑名单）
- 技术选型细节（框架版本等）留给 plan 节点
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
