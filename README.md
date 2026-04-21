# AI Workflow Foundation

一套用于创建、执行和调试基于步骤的 AI 工作流的 Claude Code 技能集合。

## 项目结构

```
ai-workflow-foundation/
├── create-ai-workflow/    # 工作流创建技能
├── execute-ai-workflow/   # 工作流执行技能
└── debug-ai-workflow/     # 工作流调试技能
```

## 三个技能的关系

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   create-ai     │ ──▶│   execute-ai    │ ──▶│   debug-ai      │
│   workflow      │    │   workflow      │    │   workflow      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
     创建和 scaffold         执行和编排            隔离调试和测试
```

1. **create-ai-workflow** - 设计并 scaffold 新的 AI 工作流
2. **execute-ai-workflow** - 运行已创建的工作流，管理状态和路由
3. **debug-ai-workflow** - 调试工作流中的单个步骤

## 核心设计理念

### Agent-First 编排模型

- **主 Agent** - 负责编排、路由、状态管理
- **子 Agent** - 执行具体的业务逻辑步骤
- **职责分离** - 主 Agent 不执行业务逻辑，子 Agent 不负责路由决策

### Markdown Fixtures

使用人类可读的 Markdown 文件定义测试用例，而非严格的 JSON：

```text
fixtures/<step-id>/<test-case>/
  prompt.md       # 子 Agent 输入
  expected.md     # 期望输出描述
  assertions.md   # 验证标准
```

### 隔离性

每个步骤都是独立单元：
- 明确的输入输出契约
- 可独立调试和测试
- 不影响全局运行状态

### 状态可追溯

- Prompt 和 Response 完整记录
- 每次执行生成可追溯的状态文件
- 支持从任意步骤恢复执行

## 快速开始

### 1. 创建工作流

```bash
/claude 创建一个新的工作流，用于自动生成代码审查意见
```

### 2. 执行工作流

```bash
/claude 运行 code-review 工作流
```

### 3. 调试步骤

```bash
# CLI 模式
/claude 调试 code-review 的 step-02-analyze 步骤

# Dashboard 模式
/claude 打开调试面板
```

## 标准目录布局

### 工作流定义（项目内）

```text
.ai-workflows/<workflow-id>/
  orchestration.md          # 路由逻辑
  workflow.spec.json        # 元数据
  steps/
    step-01-*.md            # 子 Agent 指令
  fixtures/
    step-01-*/
      <test-case>/
        prompt.md
        expected.md
        assertions.md
```

### 执行产物（项目根目录）

```text
runs/<workflow-id>/<run-id>/
  state.json                # 运行状态
  <step-id>/
    prompt.md               # 发送的提示
    response.md             # Agent 响应
    <artifacts>             # 产物文件
```

### 调试产物（项目根目录）

```text
debugs/<workflow-id>/<step-id>/<test-case>/
  response.md               # Agent 输出
  validation.md             # 验证推理
  result.json               # 元数据
```

## 工作流编排模型

### 路由规则

在 `orchestration.md` 中定义路由表：

```json
{
  "workflow_id": "example",
  "entry_step": "step-01-init",
  "routes": [
    {
      "from": "step-01-init",
      "when": "always",
      "next_step": "step-02-process"
    },
    {
      "from": "step-02-process",
      "when": "output_path_truthy",
      "path": "decision.needs_revision",
      "next_step": "step-01-init"
    }
  ]
}
```

### 步骤契约

在每个 step 文件中定义契约：

```json
{
  "step_id": "step-01-init",
  "inputs_required": ["request"],
  "outputs_written": ["normalized_request"],
  "recommended_next_step": "step-02-process"
}
```

## 技能安装

将本仓库的三个技能目录复制到你的 Claude Code skills 目录：

```bash
# 假设你克隆了本仓库到 ~/ai-workflow-foundation
cp -r ~/ai-workflow-foundation/create-ai-workflow ~/.claude/skills/
cp -r ~/ai-workflow-foundation/execute-ai-workflow ~/.claude/skills/
cp -r ~/ai-workflow-foundation/debug-ai-workflow ~/.claude/skills/
```

或者通过 MCP 配置引用本仓库。

## 示例工作流

- **PRD 生成器** - 从用户需求生成产品需求文档
- **代码审查** - 分析 PR 变更并生成审查意见
- **测试生成** - 根据代码生成单元测试
- **文档更新** - 检测代码变更并更新相关文档

## License

MIT
