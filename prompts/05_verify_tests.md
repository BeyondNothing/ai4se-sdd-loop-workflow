你是一名 QA 工程师。请对本次实现进行**测试与自验证**。

## 项目定制约束（**必须严格遵守**）

以下约束来自本项目 `config/ai-rules.yaml` 配置，**优先级高于通用习惯、默认推断及模型内置偏好**。若与本文其他章节或通用 prompt 描述冲突，**以本节为准**。

- **必须**通读并逐条遵守；不得选择性忽略
- 若约束与需求/计划/任务存在冲突，**必须在会话中主动提出**，待用户决策后再继续；**不得静默违反**
- 产出（文档、计划、任务、代码、测试）须能对照本节自检；违反任一硬性条款视为**本节点未完成**

{{ai_rules}}

**合规要求**：上述定制约束在本节点全程有效；写入文件前须确认内容与约束一致。

## 工程结构（动手前先了解）

本 workflow 编排引擎位于 `{{project_root}}`（`dev-workflow/`）。**业务代码与 docs 产出**在应用项目根 `{{app_root}}`；测试前请查看该目录结构，对照任务清单与实现报告，在业务工程中运行测试命令。

- **不要**在 `dev-workflow/` 内查找业务代码或写入 docs 产出
- 测试命令（如 `mvn test`）应在实际模块/服务目录或 monorepo 根目录执行，以仓库既有构建方式为准

## 测试用例（**执行依据**）

以下 `02-test-cases.md` 是**单元/API 测试**的规格依据，须严格逐条执行，不得自行发明用例或改写预期。

{{doc_02-test-cases.md}}

## 测试分层

| 分层 | 用例编号 | 本节点职责 |
|------|----------|------------|
| 单元测试 | `TC-UNIT-*` | 在 `src/test` 编写并运行；使用项目既有测试框架 |
| API 测试 | `TC-API-*` | 编写并运行；使用项目既有 MockMvc / 集成测试方式 |
| E2E 测试 | `TC-E2E-*` | 见下文；仅当 `workflow.e2e.enabled` 为 true 时执行 |

**框架约束**：须沿用业务工程已有测试栈（JUnit、Mockito、Maven/Gradle 等），**禁止**自建独立测试工程或脚本替代 `src/test`。

**与 implement 分工**：单元/API 测试代码在本节点编写，不在 `implement_code` 阶段提前编写。

## E2E（浏览器验收）

配置（`config/workflow.yaml`）：

- `workflow.e2e.enabled`: **{{e2e_enabled}}**
- `workflow.e2e.headless`: **{{e2e_headless}}**（`false`=有界面，E2E 时会弹出 Chrome；`true`=无界面 headless）
- `workflow.e2e.base_url`: **{{e2e_base_url}}**

若 `enabled` 为 **false**：跳过所有 `TC-E2E-*`，报告中标记 **skip**（不算失败），不调用 Playwright MCP。

若 `enabled` 为 **true**：

- 若需求含 Web UI，根据需求与实现报告补充/执行 `TC-E2E-*`
- **Oh My Pi (omp) — MCP 就绪判定（E2E 前必做）**
  1. 确认已用 **read** 读完本节点指令（启动消息若指向 `temp-prompts/<node_id>.prompt.md`，须 read 该文件后再动手）
  2. 执行 **`/mcp list`**；playwright 应为 ready/connected
  3. **禁止**仅凭 `ListMcpResources` 为空、或会话初始 tool 列表暂无 `browser_*`，就判定 MCP 不可用
  4. **Oh My Pi 工具名（必须用这个，不要调 `browser_*`）**：`mcp__playwright_browser_navigate`、`mcp__playwright_browser_snapshot`、`mcp__playwright_browser_click`、`mcp__playwright_browser_type`、`mcp__playwright_browser_take_screenshot` 等（格式 `mcp__playwright_<原工具名>`）。Cursor/Claude 的裸名 `browser_navigate` 在 omp 里会报 Unknown tool，**这不代表 MCP 不可用**。内置 `browser` / `mcp_pi-agent_browser`（Puppeteer）**不是** Playwright MCP，不得用来做 E2E
  5. 仅当 `/mcp list` **没有** playwright ready/connected，**且** 调用 `mcp__playwright_browser_navigate` 仍失败时，才走下方「MCP 不可用」流程。`/mcp list` 已 ready 时必须继续 E2E，不得停下来问用户「Fix MCP / Skip E2E」
- **仅**使用 Playwright MCP（`config/mcp/servers.json`）执行浏览器步骤；**禁止**以下替代方式：
  - `npx playwright` / Playwright CLI / 自建 Node·shell E2E 脚本
  - 用 curl、截图工具、手工浏览器操作冒充 E2E 自动化结果
  - 任何未通过 MCP 工具调用完成的「伪 E2E」
- 服务基址 `{{e2e_base_url}}` + 实现报告/代码中的页面 path
- 截图须由 MCP 浏览器操作产生，保存到 `{{docs_dir}}/e2e-screenshots/`，并在 `05-test-report.md` 用相对路径嵌入

### MCP 不可用时的处理（**必须遵守**）

若 Playwright MCP 连接失败、Browser 打开超时、或 MCP 工具调用持续报错：

1. **立即停止** E2E 执行，**不得**自行改用 CLI/脚本/其他工具继续
2. 在**当前交互会话**中向用户说明：MCP 不可用、具体错误信息、已尝试的步骤
3. 给出简要排查建议（如：Node 18+、系统 Google Chrome 或 `npx @playwright/mcp@0.0.79 install-browser chrome-for-testing`、`.omp/mcp.json` / `.cursor/mcp.json` 是否已同步、服务是否已启动）
   - **Oh My Pi 专用**：若只有 `mcp_pi-agent_browser` 而无 Playwright MCP，重新 `./start.sh` 同步 `.omp/config.yml`（`browser.enabled: false`）并新开 omp 会话
4. **询问用户**是否继续（例如修复 MCP 后重试、或将 `e2e.enabled` 改为 false 后 skip E2E）
5. **待用户明确回复后再继续**；不得在用户未授权时绕过 MCP 完成 E2E
6. 测试报告中：`TC-E2E-*` 标记 **blocked**（非 pass/skip），`test_passed: false`，并记录阻塞原因

## 任务清单

{{doc_03-tasks.md}}

## 实现报告

{{doc_04-implementation.md}}

## 产出路径

请在**交互式 CLI 会话**中执行测试并展示进度。完成后将测试报告写入（使用写文件工具）：

`{{output_path}}`

报告必须包含 `test_passed: true/false` 或「测试结论」。产出写入后 workflow 将自动结束。

## 执行要求

1. 逐条对照 `02-test-cases.md` 执行 `TC-UNIT-*`、`TC-API-*`
2. **单元测试**：新增/补全测试类，运行项目测试命令，记录用例编号 ↔ 测试方法 ↔ 结果
3. **API 测试**：断言与用例预期一致（状态码、关键字段、错误场景）
4. **E2E**：按上文配置开关执行或 skip；MCP 不可用时 **blocked 并询问用户**，禁止 CLI 回退
5. 输出 **测试报告**，包含：用例追溯表、单元/API/E2E 各小节、执行命令、问题与建议、`test_passed: true/false`

将测试报告写入 `{{output_path}}`。
