# code-puppy 代码走查：启动链路 & 用户输入响应链路

> 本文从两条路线详细走查 code-puppy 的完整执行流程，指出每个关键设计决策及其原因。

---

## 目录

- [整体架构概览](#整体架构概览)
- [路线一：启动链路](#路线一启动链路)
  - [第 0 层：进程入口](#第-0-层进程入口)
  - [第 1 层：模块级别（最优先执行）](#第-1-层模块级别最优先执行)
  - [第 2 层：main() 函数](#第-2-层main-函数)
  - [启动链路总图](#启动链路总图)
- [路线二：用户输入 → 响应](#路线二用户输入--响应)
  - [第 1 层：REPL 主循环](#第-1-层repl-主循环)
  - [第 2 层：run_prompt_with_attachments()](#第-2-层run_prompt_with_attachments)
  - [第 3 层：_runtime.run_with_mcp()](#第-3-层_runtimerun_with_mcp)
  - [第 4 层：build_pydantic_agent()](#第-4-层build_pydantic_agent)
  - [第 5 层：run_agent_task()](#第-5-层run_agent_task)
  - [第 6 层：_do_run()](#第-6-层_do_run)
  - [第 7 层：pydantic-ai 内部 + monkey-patch 拦截点](#第-7-层pydantic-ai-内部--monkey-patch-拦截点)
  - [路线二总图](#路线二总图)
- [三个最关键的设计决策](#三个最关键的设计决策)

---

## 整体架构概览

```
code-puppy/
├── code_puppy/
│   ├── __main__.py          # 进程入口（极简）
│   ├── cli_runner.py        # 主控制器：REPL、main()、interactive_mode()
│   ├── pydantic_patches.py  # monkey-patch pydantic-ai（必须最先执行）
│   ├── plugins/__init__.py  # 插件加载器（3 个来源）
│   ├── callbacks.py         # 全局事件总线（60+ hook 点）
│   ├── config.py            # 配置读写
│   ├── agents/
│   │   ├── base_agent.py    # Agent 抽象基类
│   │   ├── agent_manager.py # Agent 注册表 + 会话管理
│   │   ├── _builder.py      # pydantic-ai Agent 构建（两阶段）
│   │   ├── _runtime.py      # Agent 运行编排（重试、取消、steer）
│   │   ├── _history.py      # 历史管理纯函数（hash、token估算、pruning）
│   │   ├── _compaction.py   # 历史压缩（truncation/summarization）
│   │   └── _steer_processor.py  # 用户 steer 注入
│   └── mcp_/
│       ├── manager.py       # MCP 服务器中央协调器
│       ├── managed_server.py # MCP server 包装 + 生命周期
│       └── agent_bindings.py # agent ↔ MCP server 绑定关系
```

---

## 路线一：启动链路

### 第 0 层：进程入口

```
python -m code_puppy
    ↓
code_puppy/__main__.py: main_entry()
    ↓
asyncio.run(cli_runner.main())
```

**设计原因**：`__main__.py` 极简，只做一件事——把控制权交给 `cli_runner.main()`。
这样单元测试可以直接调用 `cli_runner.main()` 而不需要启动子进程。

---

### 第 1 层：模块级别（最优先执行）

`cli_runner.py` 顶部（行 50-51）在模块被 `import` 时立刻执行：

```python
apply_all_patches()          # 行 50：monkey-patch pydantic-ai
plugins.load_plugin_callbacks()  # 行 51：发现并加载所有插件
```

#### `apply_all_patches()` 的内容（`pydantic_patches.py`）

| patch 函数 | 替换目标 | 作用 |
|-----------|---------|------|
| `patch_user_agent()` | `pydantic_models.get_user_agent` | 把 User-Agent 改为 `Code-Puppy/{ver}`（Kimi 模型特殊处理） |
| `patch_message_history_cleaning()` | `_agent_graph._clean_message_history` | 禁用过严的 history 清理 |
| `patch_process_message_history()` | `_agent_graph._process_message_history` | 跳过 ModelRequest 末尾强制验证 |
| `patch_sse_json()` | `ServerSentEvent.json` | 修复 SSE 流式 JSON 解析 bug |
| `patch_tool_call() × 2` | `ToolManager._call_tool` | 注入 `pre_tool_call` / `post_tool_call` hooks |
| `patch_handle_call()` | `ToolManager.handle_call` | 同上（另一个入口） |
| `patch_get_tool_def()` | `ToolManager.get_tool_def` | 允许插件覆盖工具 schema |

> **关键设计原因**：必须在任何 pydantic-ai 的 class 被实例化之前打补丁。
> Python 的 class 方法替换会影响所有**后续**创建的实例，已创建的实例引用旧方法。
> 所以这两行必须在模块顶层、所有 import 之前执行。

#### `plugins.load_plugin_callbacks()` 的内容（`plugins/__init__.py:190`）

扫描三个来源，按顺序：

```
1. code_puppy/plugins/*/register_callbacks.py    ← 内置插件
2. ~/.code_puppy/plugins/*/register_callbacks.py  ← 用户插件
3. ~/.code_puppy/external_plugins.json            ← 外部插件（任意路径的 git 仓库）
```

对每个找到的 `register_callbacks.py` → `importlib.import_module()` → 模块顶层代码执行 → `register_callback("startup", my_func)` 注册到全局 `_callbacks` 字典。

> **幂等保证**：`_PLUGINS_LOADED` flag 防止重复加载（二次 import 时直接返回空列表）。

---

### 第 2 层：main() 函数（`cli_runner.py:137-512`）

```
argparse 解析参数（--prompt, --agent, --model, --resume, --skill-install...）
    ↓
启动两个渲染器（行 206-214）：
  SynchronousInteractiveRenderer(message_queue, console)  ← 旧版 Queue 渲染器（向后兼容）
  RichConsoleRenderer(message_bus, console)               ← 新版 MessageBus 渲染器
  # 两个渲染器共享同一个 display_console，避免并发写冲突
    ↓
initialize_command_history_file()  ← prompt-toolkit 的命令历史文件
    ↓
显示 ASCII Logo（pyfiglet 渐变色）
    ↓
find_available_port()  ← 为 MCP HTTP 服务找可用端口（8090-9010 范围）
    ↓
Windows Ctrl+C 三层防御（行 288-332）：
  Layer 1: disable_windows_ctrl_c()            ← 系统级关闭 Ctrl+C 信号转换
  Layer 2: install_windows_ctrl_c_swallower()  ← OS 级 SetConsoleCtrlHandler 吞掉事件
  Layer 3: signal.signal(SIGINT, handler)      ← Python 级 fallback
    ↓
load_api_keys_to_environment()  ← 从 puppy.cfg 读 API key 写入 os.environ
    ↓
Early exits：
  --skill-install   → _handle_skill_install()  → sys.exit()
  --skill-uninstall → _handle_skill_uninstall() → sys.exit()
    ↓
--model 验证：_validate_model_exists() → 不存在则列出可用 models 后 sys.exit()
--agent 验证：get_available_agents() → set_current_agent() → 不存在则 sys.exit()
    ↓
版本检查（行 428-431）：
  if "version_check" hooks 已注册 → on_version_check(current_version)  ← 插件处理
  else → default_version_mismatch_behavior()  ← 内置默认行为
    ↓
await callbacks.on_startup()  ← 行 433，触发所有 "startup" hook（插件在此初始化）
    ↓
--resume 处理：load_session() → agent.set_message_history(history)
    ↓
路由分支：
  --prompt → execute_single_prompt()  ← 单次执行后退出
  否则    → interactive_mode()        ← 进入 REPL
    ↓
finally 块（无论正常/异常退出）：
  message_renderer.stop()
  bus_renderer.stop()
  await callbacks.on_session_end()   ← 在 shutdown 之前触发，此时 agent 状态还在
  callbacks.on_shutdown()
```

---

### 启动链路总图

```
python -m code_puppy
│
├─ [模块 import 阶段 — 同步，最优先]
│   ├─ apply_all_patches()        ← monkey-patch pydantic-ai（必须最先）
│   └─ load_plugin_callbacks()    ← 扫描 3 个插件目录，import → register
│
└─ asyncio.run(main())
    ├─ 启动 2 个渲染器（Queue + Bus，共享 console）
    ├─ Windows Ctrl+C 三层防御
    ├─ load_api_keys_to_environment()
    ├─ Early exits（skill-install/uninstall）
    ├─ 参数验证（model, agent）
    ├─ on_version_check() 或 default
    ├─ on_startup()  ← 所有 startup 插件触发
    ├─ --resume 历史恢复
    └─ interactive_mode()  ←══════════════ 进入路线二
```

---

## 路线二：用户输入 → 响应

### 第 1 层：REPL 主循环（`interactive_mode()`，行 515+）

```python
while True:
    current_agent = get_current_agent()
    user_prompt = current_agent.get_user_prompt() or "Enter your coding task:"

    # prompt-toolkit 异步输入（支持历史、Tab补全、路径补全）
    task = await get_input_with_combined_completion(
        get_prompt_with_active_model(),  # 插件可以在这里注入 🟢 token 指示器
        history_file=COMMAND_HISTORY_FILE
    )
```

用户按回车后，REPL 按顺序执行过滤器：

```
输入 task
  ├─ !cmd 开头？   → execute_shell_passthrough(task) → continue（绕过 agent）
  ├─ exit/quit？   → break
  ├─ "clear"？     → task = "/clear"（重写为 slash 命令）
  ├─ 密语？        → unlock_helios() / unlock_wiggum() → continue（隐藏彩蛋）
  ├─ parse_prompt_attachments(task)   ← 解析 @file: 前缀、clipboard、URL
  ├─ 清理后以 / 开头？ → handle_command() ← slash 命令分发器 → continue
  └─ 普通文本 → run_prompt_with_attachments(agent, task, ...)  ← 进入 Agent 处理
```

---

### 第 2 层：`run_prompt_with_attachments()`（行 ~850）

```python
# 创建 asyncio Task（可取消）
agent_task = asyncio.create_task(
    agent.run_with_mcp(prompt, attachments=attachments, ...)
)

# 包在 ConsoleSpinner 里（动态显示 "thinking..."）
# 关键：spinner 切换了 console 的 Live display，防止 ANSI 输出竞争
with ConsoleSpinner(spinner_console) as spinner:
    response = await agent_task
```

> **为什么用 `asyncio.create_task` 而不是直接 `await`**：
> Task 是可取消的（`.cancel()`）。这样按 Ctrl+C / Ctrl+K 时可以向 Task 发 `CancelledError`
> 而不是粗暴地 kill 进程。

---

### 第 3 层：`_runtime.run_with_mcp()`（`_runtime.py:287`）

```python
async def run_with_mcp(agent, prompt, ...):
    reset_pause_state_at_run_start()    # 清理上次 pause 的残留状态
    prompt = _sanitize_prompt(prompt)   # 去除 Windows 复制粘贴的 UTF-16 孤项
    group_id = str(uuid.uuid4())        # 这次 run 的唯一 ID，用于日志关联

    # hook: 插件可以替换 prompt（如 claude_code_hooks 注入项目规则）
    submit_results = await on_user_prompt_submit(prompt, group_id)
    for r in submit_results:
        if isinstance(r, str): prompt = r   # 插件返回 str → 替换 prompt

    # 首次 run：构建 pydantic agent（见第 4 层）
    if agent._code_generation_agent is None:
        build_pydantic_agent(agent)

    # 首轮把 system prompt 并入 user prompt（claude-code 模式）
    prompt = _should_prepend_system_prompt(agent, prompt)
    prompt_payload = _build_prompt_payload(prompt, attachments, link_attachments)
```

然后分两个部分：

**A. 启动前 hook（在 `create_task` 之前，行 507-515）**：
```python
# 必须在 create_task 之前 await，否则 token refresh 会和 HTTP 请求竞争
await on_agent_run_start(agent_name=..., model_name=..., session_id=group_id)

agent_task = asyncio.create_task(run_agent_task())   # 行 517
```

> **精妙设计**：`on_agent_run_start` 需要先完成（刷新 token、mint credentials），
> 才能让 HTTP 请求出门。如果放在 `create_task` 之后，event loop 会立刻切换到
> `agent_task`，token 还没刷好就开始调 API。

**B. 取消/暂停监听（和 agent_task 并行）**：
```python
schedule_cancel = make_schedule_cancel(agent_task, loop)
schedule_pause  = make_schedule_pause(agent_task, loop)

# 根据配置选择监听方式：
if cancel_agent_uses_signal():
    signal.signal(SIGINT, keyboard_interrupt_handler)   # Unix: SIGINT
else:
    key_listener = start_key_listener(...)              # Windows/uvx: 键盘事件线程
```

---

### 第 4 层：`build_pydantic_agent()`（`_builder.py:347`）

首次 `run` 才执行（之后缓存在 `agent._code_generation_agent`）：

```python
# 1. 加载模型（带 fallback）
model, resolved_model_name = load_model_with_fallback(agent.get_model_name(), ...)

# 2. 组装 system prompt
instructions = _assemble_instructions(agent, resolved_model_name)
# = agent.get_full_system_prompt()          ← 核心提示词
#   + load_puppy_rules() (AGENTS.md)        ← 项目规则
#   + EXTENDED_THINKING_PROMPT_NOTE（如需要）

# 3. 加载 MCP servers
mcp_servers = load_mcp_servers(agent_name=agent.name)
# → 触发 on_pre_mcp_autostart()（插件可刷新 MCP token）
# → 启动 auto_start 的 MCP servers（fire-and-forget）

# 4. 创建 history processors（每次 LLM 调用前运行的 pipeline）
history_processor = make_history_processor(agent)   # 压缩 + 裁剪 + sanitize
steer_processor   = make_steer_history_processor(agent)  # 注入 steer 消息

# ── 两阶段构建（关键！）────────────────────────────────
# Pass 1: 空 toolset 探测，收集所有已注册工具名
probe_agent = PydanticAgent(model=model, instructions=..., toolsets=[])
register_tools_for_agent(probe_agent, agent.get_available_tools(), ...)
existing_tool_names = set(probe_agent._tools.keys())

# 过滤 MCP 工具中与 Python 工具同名的（避免 LLM 混淆）
filtered_mcp = filter_conflicting_mcp_tools(mcp_servers, existing_tool_names)

# Pass 2: 真正的 agent，含 MCP toolsets
final_pydantic = PydanticAgent(
    model=model,
    instructions=instructions,
    toolsets=filtered_mcp,
    history_processors=[history_processor, steer_processor],   # 顺序固定
    ...
)
register_tools_for_agent(final_pydantic, agent.get_available_tools(), ...)

# 插件可以 wrap 最终 agent（如 DBOS 包一层 workflow）
wrapped = on_wrap_pydantic_agent(agent, final_pydantic, ...)
agent._code_generation_agent = wrapped
```

> **两阶段构建的原因**：Pass 1 探测工具名称，Pass 2 才能过滤 MCP 同名工具，无法合并为一步。
> 若不过滤，LLM 会看到两个同名工具，行为不可预测。

---

### 第 5 层：`run_agent_task()`（`_runtime.py:444`）

```python
async def run_agent_task():
    # 清理上次中断遗留的孤立 tool call/return 对
    agent._message_history = prune_interrupted_tool_calls(agent._message_history)

    # 插件提供的 async context managers（如 DBOS 设置 workflow ID）
    run_ctxs = on_agent_run_context(agent, pydantic_agent, group_id, mcp_servers)
    async with AsyncExitStack() as stack:
        for cm in run_ctxs:
            await stack.enter_async_context(cm)
        return await _do_run(prompt_payload)

    # 异常处理（Python 3.11 ExceptionGroup / except*）：
    # except* UsageLimitExceeded → 友好提示，不 crash
    # except* McpError           → 友好提示 + /mcp logs 提示
    # except* CancelledError     → 触发 on_agent_run_cancel
    # finally → 再次 prune（run 期间可能产生新的孤立对）
```

---

### 第 6 层：`_do_run()`（`_runtime.py:330`）

```python
async def _do_run(prompt_to_use):
    # 流式检测器：监控是否有文本流出（没有则触发 fallback render）
    detector = StreamingTextDetector(event_stream_handler)

    @streaming_retry(max_attempts=3, delays=(1, 2, 4))
    async def _call():
        return await pydantic_agent.run(
            prompt_to_use,
            message_history=agent._message_history,   # 携带完整历史
            usage_limits=UsageLimits(request_limit=get_message_limit()),
            event_stream_handler=detector,            # 流式事件回调
        )

    # pydantic-ai 内部 在每次 LLM call 之前执行 history_processors：
    #   1. make_history_processor  → compaction（压缩旧消息）+ sanitize_tool_call_ids
    #   2. make_steer_history_processor → 注入 steer 消息（now-mode）

    result = await _call_with_exception_recovery()
    # _call_with_exception_recovery：try _call()，失败时 on_agent_exception() 询问插件要不要 retry

    # 完成后的循环（queue-mode steer 和 hook retry）
    while True:
        # 1) 用户在处理过程中按 Pause 注入的 steer 消息
        steer = prepare_queued_steer_injection(agent, result)
        if steer: result = await _follow_up_run(steer); continue

        # 2) 插件通过 on_agent_run_result() 请求的 retry
        hook_results = await on_agent_run_result(result, ...)
        retry_req = next((r for r in hook_results if r.get("retry")), None)
        if not retry_req: break
        result = await _follow_up_run(retry_req["prompt"])

    # 如果流式没有输出文本 → 一次性渲染 result
    if should_render_fallback(detector): render_result_without_streaming(result)
    return result
```

---

### 第 7 层：pydantic-ai 内部 + monkey-patch 拦截点

pydantic-ai 的 `agent.run()` 在内部做：

```
组装 messages（history + 新 prompt）
  → history_processors 运行（compaction, sanitize, steer 注入）
  → 发 HTTP 请求到 LLM
  → 流式接收 → event_stream_handler 把 token 实时打印到终端
  → LLM 输出 tool_call → ToolManager 拦截：

ToolManager._call_tool()  ← monkey-patched！
  ├─ await on_pre_tool_call(tool_name, args, context)
  │     插件可返回 {"blocked": True} → 工具不执行
  │     → 返回 "ERROR: {block_msg}" 给 LLM（graceful，LLM 能理解并处理）
  ├─ actual_tool_executor(args)   ← 真正执行 Python 函数
  └─ await on_post_tool_call(tool_name, args, result, duration_ms)
        (在 finally 里，确保即使工具 raise 也能观测到)

  → 工具结果追加到 message_history
  → 再次发 LLM 请求（带工具结果）
  → ... 循环直到 LLM 不再调工具
  → 最终文本输出
```

---

### 路线二总图

```
用户按回车
│
├─ Shell passthrough (!cmd) ─────────────────────── subprocess 直接执行
├─ Slash command (/xxx) ────────────────────────── command_handler 分发
│
└─ 普通文本 → run_prompt_with_attachments()
    │
    ├─ asyncio.create_task(agent.run_with_mcp())   ← 可取消的 Task
    │
    └─ _runtime.run_with_mcp()
        ├─ on_user_prompt_submit()    ← 插件可替换 prompt
        ├─ build_pydantic_agent()     ← 首次：两阶段构建（含 MCP 冲突过滤）
        ├─ on_agent_run_start()       ← await 完再 create_task（防 token 竞争）
        │
        └─ run_agent_task()
            ├─ prune_interrupted_tool_calls()
            ├─ on_agent_run_context() ← 插件 context managers
            │
            └─ _do_run()
                ├─ history_processors（compaction → steer）
                ├─ pydantic_agent.run()   ← HTTP 请求 → 流式输出
                │   └─ ToolManager._call_tool() [PATCHED]
                │       ├─ on_pre_tool_call()   ← 可 block
                │       ├─ tool_executor()
                │       └─ on_post_tool_call()
                ├─ queue-mode steer 循环
                ├─ hook retry 循环
                └─ fallback render（如流式无输出）

    → agent._message_history 更新
    → response 发到 MessageBus → RichConsoleRenderer 显示
    → REPL 等待下一次输入
```

---

## 三个最关键的设计决策

| 决策 | 位置 | 为什么这么做 |
|------|------|------------|
| `apply_all_patches()` 在模块顶层最先执行 | `cli_runner.py:50` | Python class 方法替换必须在实例化前完成，否则已创建的实例引用旧方法，patch 无效 |
| `on_agent_run_start()` 在 `create_task()` 之前 `await` | `_runtime.py:507-517` | 避免 token refresh 与 HTTP 请求的竞争条件（race condition）。`create_task` 后 event loop 立刻切换，插件没机会完成认证 |
| `build_pydantic_agent()` 两阶段构建 | `_builder.py:399-446` | Pass 1 探测工具名称，Pass 2 才能过滤 MCP 同名工具。无法合并为一步，因为必须先知道 Python 工具集才能判断 MCP 冲突 |

---

## 附：history_processor pipeline 详解

`make_history_processor(agent)` 返回的闭包在每次 LLM 请求前按顺序执行：

1. **合并新消息**：基于 `hash_message()` 去重，最新一条强制保留（防短消息碰撞）
2. **compact()**：超过 80% context 时触发
   - `truncation`：保留 system message + 最近 N 条（LIFO 填充 `protected_tokens`）
   - `summarization`：旧消息发给摘要 LLM 压缩，保留 system + 摘要 + 最近 N 条
   - 摘要失败时自动 fallback 到 truncation，不 crash
3. **清理空 `ThinkingPart`**（Extended Thinking 产生的空块）
4. **保证 history 以 `ModelRequest` 结尾**（Anthropic 强制要求，否则 400 error）
5. **`sanitize_tool_call_ids()`**：将 Kimi/OpenAI 格式的 tool_call_id（含点、冒号）替换为 Anthropic 合规格式（`toolu_xxx`）

---

*文档生成时间：2026-07-08*
