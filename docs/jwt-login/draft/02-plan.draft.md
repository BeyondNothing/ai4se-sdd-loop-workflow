# 制定计划

> 节点 ID: `create_plan`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:06:45
> 执行状态: 成功
> 备注: 节点产出已完成，已自动退出 CLI

---

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: D1
    category: tech_stack
    question: "实现语言与 Web 框架选用什么？"
    why_it_matters: "决定工程骨架、依赖、测试栈与本地启动方式；需与 monorepo 根工程及 DDD 四层包结构兼容。"
    suggestion: "沿用 monorepo 根目录已有 Java 17 + Spring Boot 3.3 + Maven 单模块；包根 com.zeiss.ecp.assistant.auth。避免另起语言栈导致与现有 pom/启动约定分叉。"
    status: resolved
    answer: "Java 17 + Spring Boot 3.3（Maven 单模块，工程根 pom.xml）；包根 com.zeiss.ecp.assistant.auth，按 DDD 四层分包。"
  - id: D2
    category: architecture
    question: "请求鉴权采用完整 Spring Security 过滤器链，还是轻量 JWT Filter？"
    why_it_matters: "影响依赖体积、配置复杂度与鉴权责任边界；须仍遵守「过滤器在 infrastructure、用例在 application」。"
    suggestion: "仅引入 spring-security-crypto（bcrypt）；用 OncePerRequestFilter 校验 Bearer JWT。不引入 spring-boot-starter-security 全栈，降低本期复杂度。"
    status: resolved
    answer: "轻量 JwtAuthFilter（OncePerRequestFilter）放在 infrastructure；仅用 spring-security-crypto 做 bcrypt。不引入完整 Spring Security 资源服务器。"
  - id: D3
    category: tech_stack
    question: "本地用户文件采用 JSON 还是嵌入式 SQLite？"
    why_it_matters: "影响基础设施仓储实现与运行依赖；需求已排除外部独立 DB。"
    suggestion: "JSON 文件（如 ./data/users.json）：实现简单、无额外驱动、满足重启后持久与预置用户。"
    status: resolved
    answer: "JSON 文件持久化（默认路径 ./data/users.json，可配置）；不引入 SQLite/JDBC。"
  - id: D4
    category: tech_stack
    question: "JWT 签发/校验库选用哪一个？"
    why_it_matters: "影响 infrastructure 中 TokenProvider 实现与依赖锁定。"
    suggestion: "jjwt 0.12.x（HS256）；与现有 pom 一致，API 清晰。"
    status: resolved
    answer: "使用 jjwt（io.jsonwebtoken）实现 domain 中 TokenProvider Port；算法 HS256。"
  - id: D5
    category: architecture
    question: "最小 Web UI 用纯静态 HTML/JS 还是服务端模板（如 Thymeleaf）？"
    why_it_matters: "影响 interfaces/infrastructure 静态资源组织与 E2E 选择器；需求要求最小可用页。"
    suggestion: "classpath:/static 下纯 HTML + 少量 JS；同源调用 /api/auth/*；token 存 localStorage。"
    status: resolved
    answer: "Spring Boot 静态资源托管纯 HTML/JS（/login 与受保护首页）；无独立前端构建、无 Thymeleaf。"
  - id: D6
    category: architecture
    question: "密码哈希 Port 与 JWT Port 定义在 domain 还是 application？"
    why_it_matters: "DDD 规范允许二者；需统一以免任务拆分与实现分叉。"
    suggestion: "二者均在 domain.port 定义（PasswordHasher、TokenProvider），infrastructure 实现；领域服务负责凭证校验编排语义。"
    status: resolved
    answer: "PasswordHasher 与 TokenProvider 接口均定义在 domain；实现在 infrastructure；CredentialDomainService 承载统一失败语义。"
```

# 计划初稿：用户 JWT 登录认证

> 节点：`create_plan` · 阶段：初稿  
> 说明：`skip_clarification=true`，决策项已按建议默认落定，无 pending。

---

## 1. 技术方案概述

在 monorepo **根目录 Spring Boot 工程**新建（或对齐）独立 **auth 限界上下文**，按 DDD 四层交付：

| 层 | 职责（本期） |
|----|----------------|
| **domain** | User 聚合、凭证校验规则、领域异常；UserRepository / PasswordHasher / TokenProvider 等 Port |
| **application** | login / me / logout 用例编排；事务边界（若有）；只依赖 Port |
| **interfaces** | REST Controller、Request/Response DTO、Assembler、统一异常映射 |
| **infrastructure** | JSON 文件仓储、bcrypt、jjwt、JwtAuthFilter、用户初始化、静态页托管与配置装配 |

部署形态：同一进程同源提供 `/login`、受保护首页与 `/api/auth/*`，默认 `http://localhost:8080`。

## 2. 模块与包划分

包根：`com.zeiss.ecp.assistant.auth`

```text
auth/
├── interfaces/rest|assembler|exception
├── application/service|dto
├── domain/model|service|repository|port|exception
└── infrastructure/persistence|security|config
```

依赖方向：interfaces → application → domain ← infrastructure（入站 Filter 可调 application 或仅解析身份后由 Controller 进用例）。

## 3. 概念数据

- **User（聚合根）**：用户标识、用户名、密码哈希
- **AccessToken（签发结果概念）**：令牌字符串、类型 Bearer、过期秒数
- **持久化**：用户记录写入本地 JSON 文件；预置 `testuser`（密码哈希，明文仅文档/测试说明）

## 4. 接口清单（清单级）

| 方法 | 路径 | 访问 | 用途 |
|------|------|------|------|
| POST | `/api/auth/login` | 公开 | 校验凭证并签发 access_token |
| GET | `/api/auth/me` | 受保护 | 返回当前用户基本信息 |
| POST | `/api/auth/logout` | 受保护 | 校验令牌有效后返回成功（无黑名单） |
| GET | `/login` | 公开 | 登录页 |
| GET | `/`（或 `/home`） | 页面侧受保护 | 受保护首页（前端依 localStorage 门禁） |

## 5. 实现步骤（建议顺序）

1. **domain**：User / UserId、领域异常、Port、CredentialDomainService  
2. **infrastructure**：JSON UserRepository、BcryptPasswordHasher、JwtTokenProvider、配置与用户初始化、JwtAuthFilter  
3. **application**：AuthApplicationService（login / me / logout）  
4. **interfaces**：AuthController、DTO、Assembler、全局异常 → 401  
5. **Web UI**：登录页 + 受保护页 + localStorage + Bearer 头  
6. **测试与文档**：领域单测、API 测试、Playwright E2E、启动与配置说明  

## 6. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 密钥误提交仓库 | `AUTH_JWT_SECRET` / gitignore 的 local yml；示例仅占位 |
| 登出后 API 仍接受旧 token | 需求已知限制；页面侧清 token 验收；文档标明 |
| 存量代码账号与需求不一致（若有） | 以需求定稿为准：`testuser` / `Test@123456` |
| Filter 写业务规则 | Filter 只做协议解析与 401；业务在 domain/application |

## 7. 预估工作量（粗估）

| 块 | 量级 |
|----|------|
| domain + ports | 0.5–1d |
| infrastructure（文件/JWT/Filter/配置） | 1–1.5d |
| application + interfaces | 0.5–1d |
| 静态 UI | 0.5d |
| 测试 + E2E + README | 0.5–1d |
| **合计** | **约 3–5 人日** |

## 8. 与 DDD 定制约束符合性

- 四层包清晰；Controller 仅调 ApplicationService  
- Repository / 出站 JWT·哈希 Port 在 domain，实现在 infrastructure  
- domain 无 Spring/JPA/Web 依赖  
- 静态页与 Filter 属适配，不替代应用/领域规则

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | create_plan |
| status | completed |
| next_node | split_tasks |
| phase | plan |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T15:06:45 |
