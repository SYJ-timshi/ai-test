# OpenClaw 架构笔记

> 生成日期：2026-07-07  
> 基于 `openclaw` 源码深度阅读，涵盖目录结构、Agent 循环、核心组件分层与 Plugin SDK 架构。

---

## 一、兄弟目录（`/WS/` 级别）用途

| 目录 | 用途 |
|------|------|
| `openclaw/` | **核心产品** — 本体运行时、插件、Gateway、CLI |
| `openclaw.ai/` *(sibling)* | 各平台安装包构建（macOS dmg、Windows exe 等） |
| `code-puppy/` | 独立轻量 AI 代码助手 App |
| `agent-test/` / `ai-test/` | 隔离的 AI 测试沙箱 |
| `backend/` | 后台服务（非核心产品运行时） |
| `fast-ai-support/` | 快速支持/运维工具 |
| `kitt-build-assets/` | CI/CD 流水线静态资源（Kitt） |
| `qdata-fa-mfe/` | QData 前端微应用 |
| `react/` | 独立 React 组件/实验 |

---

## 二、`openclaw/` 根目录各层用途

### `src/` — 核心运行时（TypeScript ESM，strict）

| 子目录 | 职责 |
|--------|------|
| `agents/` | Agent 循环核心：session 接纳、模型选择、turn 编排、工具调度、终止状态规范化 |
| `channels/` | 内置 channel 实现（非公开 API）；channel plugin 接口定义与注册 |
| `sessions/` | 会话生命周期、模型覆盖/降级 provenance、发送策略（速率/审批） |
| `tools/` | 工具描述符、可用性规划（planner）、执行分发（executor dispatch） |
| `llm/` | LLM 流式传输外观层；初始化内置 provider、注册 AI runtime host |
| `gateway/` | Gateway HTTP/WebSocket 服务；连接 UI/apps 与核心运行时 |
| `plugin-sdk/` | **插件公共契约**；插件进入核心的唯一合法边界 |
| `plugins/` | 插件加载器、manifest 解析、bundled plugin facade |
| `infra/` | 跨层基础设施：outbound 投递规划、审批、abort、事件总线 |
| `auto-reply/` | LLM 响应后处理：thinking 格式、command 检测、silent token 清理、附件注入 |
| `config/` | 配置读写、schema 类型、session config、doctor 迁移基础 |
| `routing/` | session key 解析、agent id 规范化、subagent 路由 |
| `mcp/` | MCP server/client 集成（作为 runtime 的 tool 来源之一） |
| `state/` | SQLite 状态存储访问层（Kysely helpers） |
| `memory/` | 内存插件槽位（同一时间只能激活一个 memory plugin） |
| `skills/` | 技能发现、过滤、远程技能运行时 |
| `tui/` | 终端 TUI 交互层（REPL、进度条、终端状态恢复） |
| `cli/` | CLI 命令解析、格式化、deps 类型 |
| `context-engine/` | 上下文组装：文件、工作区、prompt cache 排序 |
| `trajectory/` | Agent 运行轨迹记录（用于调试与回放） |
| `transcripts/` | 对话记录持久化 |

### `extensions/` — 插件生态

每个子目录是一个独立插件包，拥有自己的 `package.json` 和依赖：

**Provider 类**（提供模型能力）
- `anthropic/`、`openai/`、`google/`、`mistral/`、`groq/`、`xai/`、`ollama/`、`azure-openai/` 等 40+ 个
- 各自管理 auth、model catalog、流式传输适配、tool schema 兼容

**Channel 类**（提供消息通道）
- `telegram/`、`discord/`、`slack/`、`whatsapp/`、`signal/`、`line/`、`feishu/`、`imessage/` 等 30+ 个
- 负责平台消息收发、native callback 解码，不拥有产品命令逻辑

**工具/能力类**
- `browser/`、`web-readability/`、`memory-wiki/`、`memory-lancedb/`、`codex/`、`comfy/` 等

**基础设施类**
- `bonjour/`（局域网发现）、`diagnostics-otel/`（OpenTelemetry）、`policy/`、`logbook/` 等

### `packages/` — 内部共享包

| 包 | 职责 |
|----|------|
| `ai/` | LLM 抽象层：`ApiRegistry`、`stream()`/`complete()` 接口、provider 注册机制 |
| `gateway-protocol/` | Gateway 纯类型 + TypeBox schema（`AgentEvent`、`AgentParams` 等），无运行时依赖 |
| `plugin-sdk/` | 插件 SDK 类型定义（配合 `src/plugin-sdk/` 实现） |
| `agent-core/` | Agent 基础类型与行为（跨 src 与 extensions 共享） |
| `llm-core/` | LLM 消息格式、token 计数等底层类型 |
| `model-catalog-core/` | 模型目录类型与规范化 |
| `gateway-client/` | Gateway 客户端（供 apps/ui 使用） |
| `terminal-core/` | ANSI、progress line、终端状态恢复等 |
| `normalization-core/` | 字符串/值规范化 helpers（全局共用） |
| `sdk/` | 对外公开的 OpenClaw SDK（供第三方集成） |
| `tool-call-repair/` | 修复 LLM 返回的格式错误 tool call |
| `net-policy/` | 网络策略检查 |
| `speech-core/` / `media-core/` / `media-generation-core/` | 语音/媒体能力基础类型 |

### `ui/` — Web 前端

React + Vite 单页应用，通过 Gateway WebSocket 与核心通信，不直接 import `src/**`。

### `apps/` — 原生客户端

| 子目录 | 平台 |
|--------|------|
| `ios/` | iOS Swift 应用 |
| `android/` | Android 应用 |
| `macos/` | macOS 原生 App（SwiftUI，`@Observable`） |
| `macos-mlx-tts/` | macOS 本地 TTS（MLX 模型） |
| `swabble/` | 跨平台桌面壳（Electron-like） |
| `shared/` | 原生端共享代码 |

所有 App 均通过 Gateway protocol 与核心通信，不持有业务逻辑。

### 其余顶层目录

| 目录 | 职责 |
|------|------|
| `docs/` | 文档源文件（发布到 `docs.openclaw.ai`），非运行时代码 |
| `qa/` | QA 场景（YAML only，`qa/scenarios/`），自动化测试驱动 |
| `test/` | 测试辅助 helpers（`test-helpers*/`） |
| `scripts/` | 构建、CI、PR landing、Crabbox wrapper 脚本 |
| `config/` | 静态配置文件（非运行时 `src/config/`） |
| `deploy/` | 部署配置（Fly.io、Docker、Render） |
| `security/` | 安全策略、secret scanning 配置 |
| `skills/` | 核心内置 skills（新 skill 优先发布 ClawHub） |
| `patches/` | pnpm patch 补丁（精确版本锁定） |
| `git-hooks/` | Git hook 脚本 |
| `examples/` | 使用示例 |

---

## 三、完整 Agent 循环 + 组件分层解耦

### 3.1 调用链全图

```
用户输入
   │
   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ENTRY LAYER  (src/entry.ts → src/cli/)                              │
│  CLI 解析参数、环境变量、快速路径（version/help）                        │
└─────────────────────┬────────────────────────────────────────────────┘
                      │
   ┌──────────────────▼───────────────────────────────────────────┐
   │  CHANNEL INGRESS  (extensions/<channel>/src/)                │
   │  Telegram / Discord / Slack / iMessage / Gateway WebSocket   │
   │  ── 负责：接收平台消息、解码 native callback、附件预处理        │
   │  ── 不负责：产品命令树、提供商策略、feature menu               │
   └──────────────────┬───────────────────────────────────────────┘
                      │  标准化 DeliveryContext + SessionKey
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SESSION LAYER  (src/sessions/)                                      │
│  ┌───────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │
│  │ 会话生命周期   │  │ 模型覆盖 / 降级  │  │ 发送策略 send-policy │   │
│  │ admission     │  │ model-overrides  │  │ (rate / approval)   │   │
│  └───────────────┘  └─────────────────┘  └─────────────────────┘   │
│  ── 负责：接纳/拒绝请求、跨 turn 状态、level 覆盖                      │
│  ── 存储：per-agent SQLite (openclaw-agent.sqlite)                   │
└─────────────────────┬───────────────────────────────────────────────┘
                      │  SessionEntry
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT COMMAND  (src/agents/agent-command.ts)  ← 循环核心            │
│                                                                      │
│  1. resolveAgentScope()     选 agentId / workspace                  │
│  2. resolveModelSelection() 选 provider + model（支持自动降级）       │
│  3. resolveAgentDeliveryPlan() 确定回复目标 channel + to             │
│  4. ┌────────────── AGENT TURN LOOP ──────────────────┐             │
│     │  a. buildContext() 组装 transcript + tools       │             │
│     │  b. stream(llm)    → packages/ai → Provider      │             │
│     │  c. 解析 stream events                           │             │
│     │     ├─ text chunk  → 累积 / 流式输出              │             │
│     │     └─ tool_use    → Tool Planner                │             │
│     │           │                                       │             │
│     │           ▼ (src/tools/planner.ts)               │             │
│     │     ┌─────────────────────────────────┐          │             │
│     │     │  ToolDescriptor 可用性规划        │          │             │
│     │     │  availability: auth|config|env   │          │             │
│     │     └─────────┬───────────────────────┘          │             │
│     │               │ ToolExecutorRef (discriminated)   │             │
│     │        ┌──────┴──────┐                           │             │
│     │        │  kind =      │                           │             │
│     │     core│  plugin│  channel│  mcp                │             │
│     │        │        │         │    │                  │             │
│     │      core    plugin   channel  MCP Server         │             │
│     │      tool    tool     action   tool               │             │
│     │        └──────┴─────┬─────┴───┘                  │             │
│     │                     │ tool result                 │             │
│     │          ←──────────┘                             │             │
│     │  d. 追加 tool_result 消息，重新进入 loop           │             │
│     │  e. stop_reason = end_turn → 退出 loop            │             │
│     └──────────────────────────────────────────────────┘             │
│  5. sanitizePendingFinalDeliveryText()  清理 silent tokens           │
│  6. resolveAgentTerminalOutcome()       记录终止原因                  │
└─────────────────────┬───────────────────────────────────────────────┘
                      │  最终文本 + delivery plan
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OUTBOUND DELIVERY  (src/infra/outbound/)                           │
│  resolveAgentDeliveryPlan                                            │
│  turnSourceChannel ─→ 防止跨 channel 串回复                          │
│  requestedChannel / sessionLastChannel / single-configured          │
│                         ▼                                            │
│  resolveOutboundChannelPlugin()  → channel.send() / Gateway push    │
└─────────────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
  Channel Egress              Gateway WebSocket
  (Telegram/Discord...)       → ui/ / apps/ / SDK clients
```

### 3.2 各概念的职责边界与解耦规则

#### Channel（通道）— `extensions/<channel>/` + `src/channels/`

- **职责**：平台消息接收/发送、native callback 解码、附件预处理、transport 限制（字数、媒体类型）、渲染 portable presentation/actions
- **不做**：产品命令树、提供商策略、任何 `if value.startsWith('/')` 字符串推断
- **与核心解耦**：只通过 `src/plugin-sdk/channel-contract.ts` 和 `src/plugin-sdk/core.ts` 暴露的类型与核心通信；不直接 import `src/channels/**` 内部

#### Provider（提供商）— `extensions/<provider>/`

- **职责**：auth/token 管理、model catalog、流式传输适配、tool schema 兼容性修复、provider 特有错误码处理
- **与核心解耦**：通过 `packages/ai/` 的 `ApiRegistry` 注册；核心只调用 `stream()` / `complete()` 抽象，不知道具体 provider 实现
- **路由规则**：`packages/ai/src/api-registry.ts` 按 `providerId` 分发；同一 provider family 共享 helper，不加 provider-specific SDK 导出

#### Tool（工具）— `src/tools/` + 各 owner

- **核心抽象**：`ToolDescriptor`（静态定义）→ `ToolExecutorRef`（运行时执行目标），二者分离
- **四种 owner**：`core | plugin | channel | mcp` — 用**判别联合**表示，不用字符串推断
- **`ToolAvailabilityExpression`**：声明式条件（auth/config/env/plugin-enabled），planner 计算后只把可用工具发给 LLM
- **执行**：`src/tools/execution.ts` dispatch 到对应 executor；channel action 工具不经过 LLM 再推断，已在 `kind=channel` 封装

#### Session（会话）— `src/sessions/`

- **职责**：跨 turn 状态（transcript 存 SQLite）、model 覆盖与降级 provenance、admission 控制（速率/审批）、send policy
- **存储**：`agents/<agentId>/agent/openclaw-agent.sqlite`（per-agent）；全局状态用 `state/openclaw.sqlite`
- **与 channel 解耦**：session 不感知具体 channel；channel 感知由 `DeliveryContext.turnSourceChannel` 注入，仅在 outbound 路由时使用

#### Gateway & Protocol — `src/gateway/` + `packages/gateway-protocol/`

- **职责**：WebSocket/HTTP 桥接 UI / native apps / SDK clients 与核心运行时
- **`packages/gateway-protocol/`**：纯类型 + TypeBox schema（`AgentEvent`、`AgentParams`、`MessageActionParams` 等），无运行时依赖
- **热路径规则**：Gateway 不 materialize 完整 channel/plugin runtime 只为查静态描述符；用轻量 artifact resolver 优先

#### UI — `ui/` (React/Vite) + `apps/` (iOS/Android/macOS)

- 与核心通信：**只通过 Gateway protocol**（WebSocket），不直接 import 核心 `src/**`
- UI 是 Gateway 的另一个 "channel" 消费者，走同一套 `AgentEvent` 流
- `apps/macos` 等原生 App 通过 Mac gateway（`pnpm gateway:watch`）连接本地 Gateway 服务

#### Plugin SDK — `src/plugin-sdk/` + `packages/plugin-sdk/`

- 这是插件进入核心的**唯一合法入口**：`api.ts`、`runtime-api.ts`、`channel-contract.ts`、`provider-entry.ts`
- 插件不得 import `src/channels/**`、`src/agents/**`、`src/plugin-sdk-internal/**`
- 外部 plugin（npm 包）由 `extensions/` 管理自己的依赖，不进 core dist

### 3.3 关键架构约束

| 约束 | 原则 |
|------|------|
| Core 无 plugin 意识 | 核心不引用任何具体 provider/channel id 或 plugin 内部路径 |
| 单向依赖 | Plugin → PluginSDK → Core；禁止反向 |
| 存储归一 | 运行时状态只进 SQLite；不得新建 JSON sidecar 文件 |
| Fallback 是产品决策 | 加 fallback 须命名合约 + 失效模式 + 下线计划 |
| Channel 传输纯化 | Channel 不拥有命令树；命令走 `typed presentation actions` |
| Tool 声明式可用性 | `ToolAvailabilityExpression` 静态声明，planner 计算，不在 channel 里猜 |
| Gateway 协议 additive | 协议变更先加字段；不兼容变更须版本化 + 客户端跟进 |

---

## 四、Plugin SDK — `plugin-entry` 架构分析

### 4.1 文件拓扑

```
packages/plugin-sdk/src/plugin-entry.ts       ← 公开 npm 包入口（纯 re-export）
    └─ export * from src/plugin-sdk/plugin-entry.ts    ← 真实实现
           └─ type 全部来自 src/plugins/types.ts       ← 核心类型定义

src/plugin-sdk/
├── plugin-entry.ts     ← 非 channel 插件的入口契约（Provider / Tool / Service...）
├── provider-entry.ts   ← Provider 专用入口（包装 plugin-entry）
├── core.ts             ← Channel 插件入口（包装 plugin-entry + 运行时 helpers）
├── entrypoints.ts      ← SDK 子路径元数据注册表
└── api-baseline.ts     ← 公共 API 漂移检查（CI 契约锁定）
```

### 4.2 `plugin-entry.ts` — 最小插件契约

**职责**：定义所有非 channel 插件（provider、tool、service、memory、command）的标准"注册函数"。

```
DefinePluginEntryOptions            →  definePluginEntry()  →  DefinedPluginEntry
─────────────────────────────────────────────────────────────────────────────────
{ id, name, description,               normalize + lazy       host 加载的规范化对象
  kind?,                               configSchema getter
  configSchema?,                       条件 spread
  reload?,
  nodeHostCommands?,
  securityAuditCollectors?,
  register(api) }
```

**关键设计点：**

1. **类型全部来自 `import type`**（`../plugins/types.ts`），`plugin-entry.ts` 本身只持有 `definePluginEntry()` 函数和 config schema helpers 两个运行时导出，启动开销极低。

2. **`configSchema` 支持懒加载工厂**：通过 `createCachedLazyValueGetter(configSchema)` 包装，getter 首次调用时才求值，避免 schema 解析在模块导入时执行。

3. **`kind` 已废弃**：新插件应在 `openclaw.plugin.json` manifest 中声明，runtime-entry 里的 `kind` 只是旧版兼容路径。

4. **`register(api)` 是唯一运行时钩子**：插件所有能力（provider、tool、channel、service）都通过注入的 `OpenClawPluginApi` 注册，不暴露其他生命周期。

### 4.3 `provider-entry.ts` — Provider 特化层

包装 `definePluginEntry()`，专为"单 provider 插件"提供标准化路径：

```
SingleProviderPluginOptions
  ├── id / name / description
  ├── configSchema?
  └── provider:
        ├── id?（可与插件 id 不同）
        ├── label / docsPath / aliases / envVars
        ├── auth: SingleProviderPluginApiKeyAuthOptions[]   ← API key 认证方法列表
        ├── extraAuth: ProviderAuthMethod[]                ← 非 API key 方法追加
        └── catalog: buildProvider | run (两种实现路径)
```

**注册时做了什么：**

1. 每条 `auth` 条目通过 `createProviderApiKeyAuthMethod()` 转换为标准 `ProviderAuthMethod`，同时生成 wizard setup 元数据（choiceId/groupId/label 等）
2. 合并 `envVars`：来自显式声明 + 每条 auth 条目的 `envVar` 字段，去重后注册
3. catalog 有两种分支：
   - `buildProvider`（声明式）→ 走 `buildSingleProviderApiKeyCatalog()` 统一封装
   - `run`（命令式）→ 直接用自定义 `ProviderPluginCatalog.run`
4. 同时注册 `api.registerProvider()` 和 `api.registerModelCatalogProvider()` 两个槽位，后者支持 `static` 和 `live` 两种 catalog 模式

### 4.4 `core.ts` — Channel 插件入口 + 运行时 helpers

#### Registration Mode 分路

`defineChannelPluginEntry()` 内部 `register(api)` 按 `api.registrationMode` 分路：

| registrationMode | 执行内容 |
|-----------------|---------|
| `"cli-metadata"` | 只调 `registerCliMetadata?.(api)`，最小化导入开销 |
| `"discovery"` | `api.registerChannel()` + `registerCliMetadata?.(api)` |
| `"tool-discovery"` | 只调 `registerFull?.(api)` |
| `"full"` | `api.registerChannel()` + `setRuntime?.(api.runtime)` + `registerCliMetadata?.(api)` + `registerFull?.(api)` |

> **热路径关键**：Gateway 启动只需 `discovery` 模式（静态描述符），不触发 `registerFull` 中的重型 runtime 代码（send/monitor/setup 等）。

#### Chat Channel 合成器

`createChatChannelPlugin()` 将常见适配器组合成完整 `ChannelPlugin`：

```
ChatChannelSecurityOptions  →  resolveChatChannelSecurity()  →  ChannelSecurityAdapter
ChatChannelPairingOptions   →  resolveChatChannelPairing()   →  ChannelPairingAdapter
ChatChannelThreadingOptions →  resolveChatChannelThreading() →  ChannelThreadingAdapter
ChatChannelAttachedOutbound →  resolveChatChannelOutbound()  →  ChannelOutboundAdapter
```

#### Session Route Helpers

- `buildChannelOutboundSessionRoute()` — 将 channel + accountId + peer + chatType 规范化为 `baseSessionKey`
- `buildThreadAwareOutboundSessionRoute()` — 按 `precedence` 数组（`replyToId | threadId | currentSession`）选择 threadId，防止跨会话串线

### 4.5 `entrypoints.ts` — SDK 子路径注册表

SDK 的公开 API surface 由 JSON 文件驱动，分三类：

| 分类 | 含义 |
|------|------|
| `pluginSdkEntrypoints` | 所有子路径（含私有） |
| `privateLocalOnlyPluginSdkEntrypoints` | 仅 repo 内部使用，不进 `package.json exports` |
| `publicPluginSdkEntrypoints` | npm 发布的合法导入路径 |

特殊分类：
- `reservedBundledPluginSdkEntrypoints`：过渡期由 bundled plugin 支撑的 facade（如 `codex-mcp-projection`）
- `supportedBundledFacadeSdkEntrypoints`：用 bundled plugin 实现、未来替换为通用契约的子路径（如 `telegram-account`、`tts-runtime`）
- `publicPluginOwnedSdkEntrypoints`：第三方可导入的插件自有子路径（如 `memory-core-*` 系列）

`buildPluginSdkPackageExports()` 从此注册表生成 `package.json` 的 `exports` 字段，保持文档、代码、发布三者同步。

### 4.6 `api-baseline.ts` — 契约漂移防护

CI 级别的 API 稳定性保障：
- 扫描所有 `publicPluginSdkEntrypoints` 的 TypeScript 导出
- 生成结构化快照（`PluginSdkApiBaseline`）：每个导出的名称、声明文本、种类、源文件位置
- 写出 `.json`（human-readable）+ `.jsonl`（轻量 diff 检查）两种格式
- CI 对比快照：任何公开 export 的增删改都会触发 baseline drift 告警，强制明确 changelog

### 4.7 整体层次图

```
┌──────────────────────────────────────────────────────────┐
│           packages/plugin-sdk/src/plugin-entry.ts         │
│           (npm 公开包 — 纯 re-export facade)              │
└────────────────────────┬─────────────────────────────────┘
                         │ export *
┌────────────────────────▼─────────────────────────────────┐
│           src/plugin-sdk/plugin-entry.ts                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │ definePluginEntry()  ← 所有非 channel 插件的入口    │   │
│  │  ├── id / name / description                       │   │
│  │  ├── configSchema (lazy cached)                    │   │
│  │  ├── optional: reload / nodeHostCommands / audit   │   │
│  │  └── register(api: OpenClawPluginApi) → void      │   │
│  └────────────────────────────────────────────────────┘   │
│  类型来源：../plugins/types.ts (import type only)         │
└─────────────┬──────────────────────┬─────────────────────┘
              │                      │
  ┌───────────▼──────────┐  ┌───────▼────────────────────┐
  │  provider-entry.ts   │  │  core.ts                   │
  │  定义单 provider 插件  │  │  定义 channel 插件          │
  │                      │  │  + chat channel 合成器       │
  │  auth 规范化          │  │  + session route helpers    │
  │  catalog 两路实现     │  │  + registrationMode 分路    │
  │  Unified Catalog 对接 │  │  + thread binding helpers  │
  └──────────────────────┘  └────────────────────────────┘
              │                      │
              └────────┬─────────────┘
                       ▼
         src/plugins/types.ts  (OpenClawPluginApi)
         ├── api.registerProvider()
         ├── api.registerChannel()
         ├── api.registerTool()
         ├── api.registerService()
         ├── api.registerModelCatalogProvider()
         └── api.runtime  →  PluginRuntime
```

### 4.8 关键 SDK 设计约束

- **SDK surface 只增不减**（除非大版本）：公开子路径的删除/重命名是 breaking change，需先迁移所有 bundled caller 再移除
- **热路径零 runtime 代价**：`plugin-entry.ts` 和各入口文件仅静态类型 + 极少运行时代码；重型 runtime 放在 `*.runtime.ts` 子路径按需懒加载
- **家族 seam 优于 provider-specific seam**：共享行为（replay policy、tool schema compat、stream 装饰）放 SDK helpers，不为单个 provider 开专属导出
- **`api.registrationMode` 是性能安全阀**：Gateway 启动、CLI help 等快速路径走 `cli-metadata/discovery` 不触发完整 channel runtime
