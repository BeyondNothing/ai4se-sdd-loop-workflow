# DDD 四层架构设计规范（默认）

本 monorepo 的业务代码采用 **领域驱动设计（DDD）四层架构**。需求分析、计划、任务拆分、实现、测试各阶段均须遵守本规范。

---

## 1. 四层定义与包结构

推荐 Maven 模块或包根：`com.<company>.<product>.<boundedContext>`

| 层 | 包名建议 | 职责 |
|----|----------|------|
| **接口层** | `..interfaces..` | 对外暴露 API；协议适配；入参/出参 DTO；不含业务规则 |
| **应用层** | `..application..` | 用例编排；事务边界；调用领域对象完成业务流程 |
| **领域层** | `..domain..` | 核心业务模型与规则；领域服务；仓储接口（Port） |
| **基础设施层** | `..infrastructure..` | 仓储实现；数据库/缓存/消息/第三方 SDK 适配 |

示例目录：

```text
src/main/java/com/example/auth/
├── interfaces/
│   ├── rest/           # Controller、Request/Response DTO
│   └── assembler/      # DTO ↔ 领域对象转换
├── application/
│   ├── service/        # ApplicationService / UseCase
│   └── command/        # 命令对象（可选）
├── domain/
│   ├── model/          # Entity、AggregateRoot、ValueObject
│   ├── service/        # DomainService（纯领域逻辑）
│   ├── repository/     # Repository 接口（Port）
│   └── event/          # 领域事件（可选）
└── infrastructure/
    ├── persistence/    # Repository 实现、PO、Mapper
    ├── config/         # Spring 配置、Bean 装配
    └── external/       # 外部系统客户端
```

---

## 2. 层间依赖关系（必须遵守）

**依赖方向只能由外向内，领域层是核心，不依赖任何外层。**

```text
        ┌─────────────┐
        │  接口层      │  interfaces
        └──────┬──────┘
               │ 仅依赖
               ▼
        ┌─────────────┐         ┌─────────────┐
        │  应用层      │ ◄────── │ 基础设施层   │  入站适配：Webhook / MQ 消费 /
        └──────┬──────┘  可依赖  │             │  定时任务 等调用 ApplicationService
               │ 仅依赖         └──────┬──────┘
               ▼                       │ 实现 Port / 出站 HTTP 客户端
        ┌─────────────┐                │
        │  领域层      │ ◄──────────────┘  依赖倒置：实现 domain 中定义的接口
        └─────────────┘
```

| 从 → 到 | 是否允许 | 说明 |
|---------|----------|------|
| 接口层 → 应用层 | ✅ | Controller 只调用 ApplicationService |
| 接口层 → 领域层 | ❌ | 禁止 Controller 直接操作 Entity / Repository |
| 应用层 → 领域层 | ✅ | 编排聚合、调用领域服务、通过 Port 持久化或调用外部能力 |
| 应用层 → 基础设施层 | ❌ | 禁止依赖具体实现类；只依赖 domain 中定义的 Port 接口 |
| 领域层 → 应用/接口/基础设施 | ❌ | 领域层零 outward 依赖 |
| 基础设施层 → 领域层 | ✅ | 实现 Repository、外部网关 Port 等 domain 接口 |
| 基础设施层 → 应用层 | ✅ | **入站适配**场景：Webhook 处理器、MQ Listener、Scheduler 调用 ApplicationService 触发用例 |
| 基础设施层 → 接口层 | ❌ | 禁止反向依赖表现层 |

**外部 API 两种方向（不要混为一谈）：**

| 方向 | Port 定义位置 | 实现位置 | 谁调用谁 |
|------|---------------|----------|----------|
| **出站**（本系统调外部 HTTP/RPC） | `domain` 或 `application` 中定义 `XxxClient` / `XxxGateway` 接口 | `infrastructure/external` 中 HTTP 实现 | ApplicationService 调 Port 接口 → Infra 实现发请求 |
| **入站**（外部回调/Webhook/MQ 进本系统） | 无 Port；由适配器直接触发用例 | `infrastructure` 中 Listener / WebhookHandler | Infra 适配器 → 调用 ApplicationService |

出站外部 API **不需要** infrastructure 依赖 application：接口在 domain/application，实现在 infrastructure，应用层通过 DIP 使用接口即可。

入站外部 API **需要** infrastructure 依赖 application：适配器收到外部事件后，必须调用 ApplicationService 才能进入用例编排，这是合理依赖。

---

## 3. 依赖倒置原则（DIP）

1. **高层模块不依赖低层模块**，二者都依赖抽象。
2. **抽象（Port）在领域层或应用层定义**，实现在基础设施层完成。

### 3.1 仓储与出站外部 API（典型 DIP）

```java
// domain/repository/UserRepository.java — Port 在领域层
public interface UserRepository {
    Optional<User> findByUsername(String username);
    void save(User user);
}

// domain/gateway/PaymentGateway.java — 出站外部 API 的 Port 也在 domain（或 application）
public interface PaymentGateway {
    PaymentResult charge(Money amount, PaymentOrder order);
}

// infrastructure/persistence/UserRepositoryImpl.java
@Repository
public class UserRepositoryImpl implements UserRepository { ... }

// infrastructure/external/PaymentGatewayImpl.java — 出站 HTTP 调第三方
@Component
public class PaymentGatewayImpl implements PaymentGateway {
    // RestClient / WebClient 等仅出现在本类，ApplicationService 只见 PaymentGateway 接口
}
```

- ApplicationService 注入 `UserRepository`、`PaymentGateway` 等**接口**；运行时由 Spring 注入 infrastructure 实现。
- **出站外部 API 不需要 infrastructure → application**：调用链是 Application → Port 接口 ← Infrastructure 实现。

### 3.2 入站外部 API（Infrastructure → Application）

```java
// infrastructure/messaging/OrderPaidEventListener.java
@Component
public class OrderPaidEventListener {
    private final OrderApplicationService orderApplicationService;

    @RabbitListener(queues = "order.paid")
    public void onMessage(OrderPaidMessage msg) {
        orderApplicationService.confirmPayment(msg.getOrderId()); // 入站适配触发用例
    }
}
```

- Webhook、MQ 消费、定时补偿任务等**入站适配器**放在 infrastructure，**允许并鼓励**依赖 ApplicationService。
- 适配器只做协议解析与参数转换，业务编排仍留在 application / domain。

### 3.3 共同约束

- 禁止在 `domain` 包中出现 `@Entity`（JPA）、`RestTemplate`、`WebClient` 等基础设施细节。
- 禁止在 `domain` 中 import `interfaces.*` 或 `infrastructure.*`。
- 禁止 **application** 直接 import `infrastructure.*` 具体实现类（应只面向 Port 接口）。

---

## 4. 各层编码与设计规范

### 4.1 接口层（interfaces）

**做什么**

- 接收 HTTP/RPC 请求，校验格式（Bean Validation），调用应用层，返回 DTO。
- 认证/鉴权入口（Filter、Interceptor）可放本层或 infrastructure，但不写业务规则。

**不做什么**

- 不含业务判断（如「密码是否正确」「库存是否足够」）。
- 不直接访问数据库、缓存、Repository 实现类。

**规范**

- Controller 方法薄：参数校验 → 调用 ApplicationService → Assembler 转 DTO。
- Request/Response 命名为 `*Request`、 `*Response`，与领域模型分离。
- 统一异常由 `@ControllerAdvice` 处理，Controller 不 catch 业务异常。

---

### 4.2 应用层（application）

**做什么**

- 一个 public 方法对应一个用例（如 `login`、`getCurrentUser`）。
- 定义事务边界（`@Transactional` 放在本层，不放 domain）。
- 加载聚合、调用领域行为、通过仓储接口持久化、发布领域事件。

**不做什么**

- 不承载核心不变业务规则（应下沉到 Entity / DomainService）。
- 不包含 SQL、HTTP 调用细节。

**规范**

- 命名：`XxxApplicationService` 或 `XxxUseCase`。
- 入参可用 Command 对象；出参可用简单 DTO 或领域只读视图，不暴露 mutable Entity 给接口层。
- 跨聚合协调放应用层；单聚合内规则放领域层。

---

### 4.3 领域层（domain）

**做什么**

- 定义 Aggregate Root、Entity、Value Object，封装不变量与业务行为。
- 定义 Repository **接口**、DomainService（无状态领域逻辑）。
- 抛出领域异常（如 `InvalidCredentialsException`），由上层翻译为 HTTP 状态码。

**不做什么**

- 不依赖 Spring、JPA、JSON 库（除 JDK 标准库）。
- 不关心数据如何存储、如何暴露为 REST。

**规范**

- 聚合根负责维护一致性边界；外部只能通过聚合根修改内部实体。
- Value Object 不可变、按值相等。
- 领域方法用业务语言命名（`changePassword`、`issueToken`），避免 `setXxx` 贫血模型。
- Repository 接口以聚合根为粒度：`Optional<User> findById(UserId id)`。

---

### 4.4 基础设施层（infrastructure）

**做什么**

- 实现 `domain.repository` 及 **出站** Port（`XxxGateway` / `XxxClient`）：JPA、HTTP Client、SDK 封装等。
- **入站**适配：Webhook Controller（非 REST 对外 API 时）、MQ Listener、Scheduler，收到外部事件后调用 ApplicationService。
- 持久化 PO 与领域对象互转；框架配置与 Bean 装配。

**不做什么**

- 不把核心业务规则写在 Repository 实现、HTTP 客户端或 SQL 里（除纯技术校验）。
- 不让 PO 或第三方 SDK 类型泄漏到 application / interfaces 层。

**规范**

- **出站外部 API**：在 domain/application 定义 Port 接口；本层 `*Impl` 内使用 RestClient/WebClient，ApplicationService 不感知 HTTP 细节。
- **入站外部 API**：Listener/Handler 在本层，注入并调用 ApplicationService；不在 Listener 里写完整业务流程。
- PO 与 Entity 分离；RepositoryImpl 内完成 `toDomain()` / `toPO()`。
- 框架配置（`@Configuration`）集中在本层；通过 `@Bean` 将 Port 接口绑定到实现。

---

## 5. 计划 / 任务 / 实现阶段的落地要求

| 阶段 | 要求 |
|------|------|
| **需求 / 计划** | 模块划分按四层描述；接口清单归属接口层，用例归属应用层，核心概念归属领域层 |
| **任务拆分** | 任务按层拆分并标明依赖顺序：domain → infrastructure → application → interfaces |
| **代码实现** | 新建类必须落在正确包；禁止跨层违规 import |
| **测试** | `02-test-cases.md` 须含 `TC-UNIT-*` / `TC-API-*`；**单元与 API 测试在 `verify_tests` 节点编写并运行**，严格按用例执行；须使用业务工程既有测试框架与 `src/test` 约定，**禁止**自建独立测试体系 |

---

## 6. 反模式（禁止）

- **贫血领域模型**：Entity 只有 getter/setter，逻辑全在 Service。
- **上帝 ApplicationService**：所有逻辑堆在一个类，领域层空壳。
- **Controller 调 Repository**：跳过应用层与领域行为。
- **领域层 import Spring / JPA**：破坏可测试性与 DIP。
- **跨层循环依赖**：如 application 与 infrastructure 互相 import 具体类；或 infrastructure 依赖 interfaces。

---

## 7. 自检清单（实现完成后）

- [ ] 四层包结构清晰，无错层放置
- [ ] `domain` 包无 outward 依赖（无 Spring/JPA/Controller import）
- [ ] Repository 接口在 `domain`，实现在 `infrastructure`
- [ ] Controller 仅依赖 ApplicationService
- [ ] 核心业务规则在 Entity / DomainService 中可找到
- [ ] 出站外部 API 已定义 Port，HTTP/SDK 细节仅在 infrastructure 实现中
- [ ] 入站适配（Webhook/MQ/Scheduler）在 infrastructure，通过 ApplicationService 触发用例
- [ ] 依赖方向符合「外 → 内」，出站能力遵循 DIP，入站适配允许 infra → application
