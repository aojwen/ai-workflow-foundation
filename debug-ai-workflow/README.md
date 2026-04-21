# debug-ai-workflow

AI 工作流调试技能 - 用于隔离调试和测试 AI 工作流的单个步骤。

## 功能特性

- **隔离调试** - 一次调试一个步骤，不影响主运行状态
- **Markdown Fixtures** - 使用人类可读的 Markdown 文件进行测试
- **双模式执行** - 支持 CLI 批处理和交互式 Dashboard
- **详细日志** - 每次调试结果永久保存在 `debugs/` 目录
- **可视化面板** - 暗色主题 Dashboard，三栏布局展示完整调试信息

## 适用场景

- 需要调试工作流中某个特定步骤的行为
- 想要针对特定测试用例验证步骤输出
- 需要查看 Agent 响应和验证逻辑的详细信息

## 使用方法

### CLI 模式（默认）

```bash
/claude 调试工作流 <workflow-id> 的 <step-id> 步骤
```

或指定测试用例：

```bash
/claude 调试工作流 <workflow-id> 的 <step-id> 步骤，使用 <test-case> 测试用例
```

### Dashboard 模式（交互式）

```bash
/claude 打开调试面板
```

Dashboard 功能：
- 可视化选择工作流、步骤、测试用例
- 点击按钮查看 Prompt/Expected/Assertions
- 一键执行测试并查看结果
- 实时显示执行时间线和验证结果

## 执行模式

### 1. CLI 模式（默认）
如果用户要求调试工作流或步骤但未指定模式，使用批处理执行。

**Agent 操作**：调用 `scripts/debug_cli.py` 执行指定步骤的测试用例。

**行为**：
- 未指定测试用例时运行该步骤的所有测试用例
- 使用 `claude -p` 执行子 Agent 并验证
- 生成 HTML 报告并总结结果

### 2. Dashboard 模式（交互式）
如果用户明确要求"dashboard"、"UI"或"交互模式"。

**Agent 操作**：调用 `scripts/debug_dashboard.py` 启动 Web 服务器。

**行为**：
- 自动打开浏览器访问 Dashboard
- 用户可视化选择工作流、步骤、测试用例
- 点击"Run Test"触发测试
- Agent 在后台运行，用户可在浏览器交互

## 调试产物

每次调试执行的结果永久保存在项目根目录的 `debugs/` 目录下：

```text
debugs/
  <workflow-id>/
    <step-id>/
      <test-case>/
        response.md       # 子 Agent 的原始输出
        validation.md     # 验证推理和决策
        result.json       # 执行元数据（时间、状态等）
```

## Fixture 结构

测试用例基于 Markdown fixtures：

| 文件 | 说明 |
|------|------|
| `fixtures/<step-id>/<test-case>/prompt.md` | 发送给子 Agent 的提示 |
| `fixtures/<step-id>/<test-case>/expected.md` | 期望结果的描述性总结 |
| `fixtures/<step-id>/<test-case>/assertions.md` | 主 Agent 验证的 Markdown 标准 |

## 设计原则

### 隔离性
调试单个步骤时不影响主运行状态，结果写入独立的 debug 目录。

### Markdown Fixtures
使用人类可读的 Markdown 文件定义提示、期望输出和断言。

### Agent 执行
脚本使用 `claude -p` CLI 命令执行子 Agent 并进行验证。

### 主 Agent 验证
主 Agent 负责比较观察结果与期望，判断调试是否通过。

## Dashboard 界面

Dashboard 采用三栏暗色主题布局：

- **左栏** - Test Fixtures（Prompt/Expected/Assertions 切换查看）
- **中栏** - Execution Timeline（执行时间线） + Agent Response
- **右栏** - Validation Result（验证推理和结果）

支持功能：
- 侧边栏折叠/展开
- 切换查看不同类型的 Fixture
- 可视化执行状态指示器
- 执行时间统计

## 相关技能

- **create-ai-workflow** - 创建新的工作流
- **execute-ai-workflow** - 执行完整的工作流

## 示例

```bash
# CLI 模式调试
/claude 调试 prd-generator 工作流的 step-02-research 步骤

# 指定测试用例
/claude 调试 code-review 的 step-01-analyze，使用 edge-case-large-diff 测试用例

# Dashboard 模式
/claude 打开调试面板，我要交互调试工作流
```

## 调试循环

1. 主 Agent 识别目标步骤
2. 加载步骤文件和 fixture/snapshot
3. 委托子 Agent 执行步骤（除非只是结构检查）
4. 主 Agent 验证结果（结构、语义、副作用）
5. 记录观察输出、期望输出、不匹配、可能原因
6. 决定：重跑步骤、修复步骤、更新 fixture、应用到主运行
