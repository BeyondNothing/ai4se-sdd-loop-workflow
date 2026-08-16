# 实现报告：用户 JWT 登录认证

> 节点 ID: `implement_code`  
> 生成时间: 2026-08-16T15:10:00+08:00  
> 工程根: 仓库根目录（`pom.xml`，包根 `com.zeiss.ecp.assistant.auth`）

---

## 1. 已完成任务

| ID | 标题 | 状态 |
|----|------|------|
| TASK-01 | 领域层：User 聚合、Port、凭证领域服务与异常 | 完成 |
| TASK-02 | 基础设施：JSON 仓储、bcrypt、JWT、配置与预置用户 | 完成 |
| TASK-03 | 基础设施：JwtAuthFilter | 完成 |
| TASK-04 | 应用层：login / me / logout | 完成 |
| TASK-05 | 接口层：Controller、DTO、Assembler、全局异常 | 完成 |
| TASK-06 | 最小静态 UI（localStorage） | 完成 |
| TASK-07 | API 自动化测试 | 完成（`mvn test` 通过） |
| TASK-08 | E2E 场景说明 + README | 完成（浏览器 E2E 由 verify_tests / Playwright MCP 执行） |

---

## 2. 变更文件列表及说明

### 领域层（TASK-01）

| 路径 | 说明 |
|------|------|
| `src/main/java/.../auth/domain/model/User.java` | 用户聚合根；`matchesPassword` 行为 |
| `src/main/java/.../auth/domain/model/UserId.java` | UUID 值对象 |
| `src/main/java/.../auth/domain/repository/UserRepository.java` | 仓储 Port |
| `src/main/java/.../auth/domain/port/PasswordHasher.java` | 密码哈希 Port |
| `src/main/java/.../auth/domain/port/TokenProvider.java` | JWT 签发/解析 Port（`IssuedToken` / `TokenClaims`） |
| `src/main/java/.../auth/domain/service/CredentialDomainService.java` | 统一无效凭证语义 |
| `src/main/java/.../auth/domain/exception/*.java` | InvalidCredentials / InvalidToken / Unauthorized |

### 基础设施层（TASK-02 / TASK-03）

| 路径 | 说明 |
|------|------|
| `.../infrastructure/persistence/FileUserRepository.java` | JSON 文件仓储 |
| `.../infrastructure/persistence/UserFileRecord.java` | 文件 PO（不出界） |
| `.../infrastructure/persistence/UserDataInitializer.java` | 预置 **testuser**（bcrypt 哈希） |
| `.../infrastructure/security/BcryptPasswordHasher.java` | spring-security-crypto |
| `.../infrastructure/security/JwtTokenProvider.java` | jjwt HS256；claims: sub/username/iat/exp |
| `.../infrastructure/security/JwtAuthFilter.java` | OncePerRequestFilter；公开路径放行；401 JSON |
| `.../infrastructure/config/AuthProperties.java` | secret / expiration / users.file |
| `.../infrastructure/config/AuthInfrastructureConfig.java` | Bean、Filter 注册、`/login` → `login.html` |
| `.../infrastructure/config/JacksonConfig.java` | SNAKE_CASE |
| `src/main/resources/application.yml` | 端口 8080、JWT/用户文件配置 |

### 应用层（TASK-04）

| 路径 | 说明 |
|------|------|
| `.../application/service/AuthApplicationService.java` | login / currentUser / logout |
| `.../application/dto/AccessTokenResult.java` | accessToken、tokenType、expiresIn |
| `.../application/dto/CurrentUserView.java` | userId、username |

### 接口层（TASK-05）

| 路径 | 说明 |
|------|------|
| `.../interfaces/rest/AuthController.java` | `/api/auth/login|me|logout` |
| `.../interfaces/rest/LoginRequest|LoginResponse|MeResponse|LogoutResponse|ErrorResponse.java` | DTO |
| `.../interfaces/assembler/AuthAssembler.java` | 应用出参 → 响应 DTO |
| `.../interfaces/exception/GlobalExceptionHandler.java` | 401/400 统一 ErrorResponse |

### UI / 文档 / 测试（TASK-06–08）

| 路径 | 说明 |
|------|------|
| `src/main/resources/static/login.html` | 登录页；提示 testuser |
| `src/main/resources/static/index.html` | 受保护首页；展示 me；登出 |
| `src/main/resources/static/js/auth.js` | localStorage + Bearer API |
| `src/main/resources/static/css/app.css` | 最小样式 |
| `src/test/java/.../CredentialDomainServiceTest.java` | 领域单测 |
| `src/test/java/.../AuthApiIntegrationTest.java` | MockMvc 集成测试（验收 1–6） |
| `src/test/resources/application.yml` | 测试密钥与临时用户文件 |
| `README.md` | 启动、配置、测试账号、已知限制 |
| `docs/jwt-login/e2e-scenarios.md` | Playwright E2E 场景与选择器 |
| `application-local.yml.example` | 密钥占位（真实密钥不入库） |
| `pom.xml` | Spring Boot 3.3 / jjwt / validation / crypto |

### 启动入口

| 路径 | 说明 |
|------|------|
| `src/main/java/com/zeiss/ecp/assistant/AuthApplication.java` | Spring Boot 主类 |

---

## 3. 关键设计决策

1. **账号口径统一为 testuser / Test@123456**（决策 T6）：覆盖初始化器、登录页提示、README、领域/集成测试；删除旧 `data/users.json`（含 admin）以便重启后重新种子化。
2. **轻量 JwtAuthFilter**，不引入 `spring-boot-starter-security`；仅用 `spring-security-crypto` 做 bcrypt。
3. **页面门禁与 API 鉴权双轨**：静态 `/`、`/login` 由 Filter 放行，前端用 localStorage 门禁；`/api/auth/me`、`/logout` 由 Filter 强制 Bearer。
4. **登出无黑名单**：`logout` 仅校验令牌有效后返回 `{message: logged_out}`；客户端清 token。
5. **Jackson SNAKE_CASE**：对外 JSON 字段为 `access_token`、`user_id` 等；文件仓储使用独立 ObjectMapper，避免污染磁盘字段名。
6. **密钥注入**：`AUTH_JWT_SECRET` / `application-local.yml`（gitignore）；启动时校验至少 32 字节。

---

## 4. 已知限制与未完成项

| 项 | 说明 |
|----|------|
| 登出后 API 侧旧 token | 未过期 access_token 在 API 仍可能有效（已知限制，文档已说明） |
| 浏览器 E2E 实测 | 本节点提供场景说明与入口 URL；实际 Playwright MCP 跑通归 **verify_tests** |
| 注册 / Refresh / RBAC / 黑名单 | 明确不在本期范围 |

无阻塞本期验收的未完成编码任务。

---

## 5. Web / E2E 入口

基址与 `config/workflow.yaml` → `workflow.e2e.base_url` 一致：`http://localhost:8080`。

| 用途 | 完整 URL |
|------|----------|
| 登录页 | http://localhost:8080/login |
| 受保护首页（登录后） | http://localhost:8080/ |
| 登出入口 | 受保护首页按钮 `#logout-btn`（调用 `POST /api/auth/logout` 后回登录页） |

相关 API（同源）：

| 方法 | URL |
|------|-----|
| POST | http://localhost:8080/api/auth/login |
| GET | http://localhost:8080/api/auth/me |
| POST | http://localhost:8080/api/auth/logout |

预置账号：`testuser` / `Test@123456`。

E2E 步骤摘要：打开登录页 → 登录成功进首页看 me → 登出 → 再访首页须回登录页。详见 `docs/jwt-login/e2e-scenarios.md`。

---

## 6. 架构自检（DDD）

- [x] 四层包结构：`domain` / `application` / `interfaces` / `infrastructure`
- [x] `domain` 无 Spring / JPA / Servlet / jjwt 依赖
- [x] Repository / PasswordHasher / TokenProvider 在 domain，实现在 infrastructure
- [x] Controller 仅依赖 `AuthApplicationService` + Assembler
- [x] 凭证规则在 `CredentialDomainService` / `User.matchesPassword`
- [x] 出站 JWT/哈希走 DIP；入站 Filter 在 infrastructure
- [x] 依赖方向外 → 内

---

## 7. 本地验证命令

```bash
# 仓库根目录
cp application-local.yml.example application-local.yml   # 若尚未配置
mvn test
mvn spring-boot:run
```

`mvn test` 已在本节点执行通过（领域单测 + AuthApiIntegrationTest）。

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | implement_code |
| status | completed |
| next_node | verify_tests |
| phase | implement |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T15:10:13 |
