# AI 大模型高级工程师学习计划

> 目标职位：AI 大模型高级开发工程师（腾讯云 TI-One/OpenClaw 龙虾/Agent/MCP 方向）
> 基于全栈开发背景，预计 **12-16 周** 达到面试水平。

---

## 能力地图

```
已有基础（全栈）
  ├── HTTP/RPC 协议理解    → 快速上手 MCP JSON-RPC
  ├── 服务端开发经验        → Agent 工具调用、服务编写
  └── 工程化/调试能力       → 源码改造、排障
```

---

## 第一阶段：LLM + Agent 基础（第 1-2 周）

**目标**：建立 LLM 工程调用体系，理解 Agent 本质

### Day 1-3: LLM API 工程实战
- OpenAI / Anthropic API 调用（Chat/Stream/Function Calling）
- Prompt Engineering（System/User/Assistant 角色）
- Token 计算、上下文管理

### Day 4-7: Agent 核心模式
- ReAct（Reasoning + Acting）推理链路
- CoT（Chain of Thought）引导
- Tool Calling 工具调用标准流程
- 手写一个最小 Agent（不用框架）：

```python
while not done:
    思考 → 选工具 → 执行 → 观察 → 继续
```

### Day 8-14: RAG 系统手搓
- Embedding 原理 + 向量数据库（Milvus/Chroma）
- 文档切片、检索、Rerank
- 完整 RAG Pipeline 从零实现

**阶段产出**：一个纯手写的 ReAct Agent + RAG 系统，不依赖 LangChain

---

## 第二阶段：MCP 协议深度（第 3-4 周）

**目标**：能独立编写 MCP Server/Client，这是面试硬考点

### Week 3: 协议层理解
- JSON-RPC 2.0 规范（request/response/notification）
- MCP 标准协议文档精读（modelcontextprotocol.io）
  - Tools（工具声明与调用）
  - Resources（资源暴露）
  - Prompts（提示模板）
  - Sampling（模型调用）
- MCP 传输层：stdio / SSE / HTTP

### Week 4: 手搓 MCP Server + Client

```python
# 目标：不用 SDK，手写 MCP Server
class McpServer:
    def handle_initialize(self, params): ...
    def handle_tools_list(self): ...
    def handle_tools_call(self, name, arguments): ...
    def handle_resources_list(self): ...

# 再用官方 SDK 对比，理解封装层做了什么
```

**阶段产出**：
- 手写一个 MCP 天气查询 Server（不用 SDK）
- 手写 MCP Client 连接它
- 实现权限管控（工具白名单、调用鉴权）
- 多 MCP Server 并行调度（Promise.all 模式）

---

## 第三阶段：OpenClaw 龙虾框架（第 5-10 周）⭐ 核心

**目标**：能手搓部署、改源码、定制 MCP 对接、现场实操

### Week 5: 环境搭建 & 源码编译
- 从 GitHub clone 源码（不用 docker 一键包）
- 手动配置依赖、编译、启动
- 理解项目目录结构
- 跑通 Hello World 流程，用调试器单步跟踪

### Week 6-7: 吃透四大核心模块

#### 【1】Lobster 工作流引擎
- DAG 节点定义、执行顺序
- 条件分支、循环节点
- 节点间数据传递机制
- 手写一个自定义节点类型

#### 【2】三层记忆系统
- 工作记忆（当前对话上下文）
- 情景记忆（历史对话检索）
- 知识记忆（外部知识库/RAG）
- 三层如何协同：优先级、注入时机

#### 【3】Gateway 网关
- 请求路由逻辑
- 模型适配层（多模型统一接口）
- 限流、鉴权、日志
- 新增自定义 LLM 适配

#### 【4】技能插件机制
- 插件注册/发现机制
- 插件生命周期
- 手写一个完整插件（含工具调用）

### Week 8-9: 源码改造实战（面试必考）

改造任务清单：
- 修复一个框架 Bug（自己找或构造场景）
- 扩展 Lobster 新节点类型（如：并行分支节点）
- 定制 MCP 对接逻辑（替换默认 MCP 客户端）
- 添加新的记忆策略（如：基于重要性的记忆淘汰）
- 修改 Gateway 支持 streaming 新模型

### Week 10: 全链路排障能力
- 常见启动失败场景复现 + 排查
- 工作流执行卡死的定位方法
- MCP 调用失败的抓包分析
- 性能瓶颈定位（内存泄漏、慢节点）

---

## 第四阶段：多 Agent 协作（第 11-12 周）

### Week 11: 多 Agent 架构
- Orchestrator + Worker 模式
- Agent 间消息传递（共享记忆 or 消息队列）
- 任务分解与汇总（Planner → Executor → Reviewer）
- 死循环检测与终止条件

### Week 12: 复杂长任务编排
- 需求分析 Agent → 代码生成 Agent → 测试 Agent
- 错误恢复与重试策略
- 完整 Demo：自动代码审查多 Agent 系统

---

## 第五阶段：腾讯云 TI-One 专项（第 13-14 周）

- TI-One 平台文档精读
- 在 TI-One 上部署 OpenClaw
- 对接腾讯云向量数据库（VDB）
- 熟悉 Tencent 技术栈：TRTC/COS/云函数

---

## 第六阶段：面试准备（第 15-16 周）

### 现场实操准备（龙虾框架）
- [ ] 能在 30 分钟内从源码编译启动
- [ ] 能现场改一个节点类型
- [ ] 能写一个 MCP Tool Server
- [ ] 能解释三层记忆的数据流向

### 高频面试题
- ReAct 和 CoT 区别，各自适合什么场景？
- MCP 和 Function Calling 的区别？
- 多 Agent 如何避免循环调用？
- RAG 召回率低怎么优化？
- 工作流引擎如何处理节点失败？

---

## 学习资源

| 资源 | 用途 |
|------|------|
| [modelcontextprotocol.io](https://modelcontextprotocol.io) | MCP 官方文档 |
| OpenClaw GitHub | 框架源码 |
| Anthropic Claude 文档 | Tool Use 规范参考 |
| LangGraph 源码 | 工作流引擎思路参考 |
| AutoGen 源码 | 多 Agent 模式参考 |

---

## 每周时间分配建议

每天 2-3 小时：
- **60%** 动手写代码（最重要）
- **25%** 读源码
- **15%** 看文档/视频

**关键原则**：永远用"能不能改源码"衡量自己的掌握程度，不要停留在"会用 API"层面。

**最快路径**：先把 MCP 手搓吃透（2周），再啃龙虾源码（6周），面试把握最大。
