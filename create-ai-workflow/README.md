# create-ai-workflow

AI 工作流创建技能 - 用于设计和 scaffold 新的基于步骤的 AI 工作流。

## 功能特性

- **引导式创建** - 通过结构化问答收集工作流定义所需的全部信息
- **Markdown Fixtures** - 使用人类可读的 Markdown 文件定义测试用例
- **Agent-First 架构** - 主 Agent 负责编排路由，子 Agent 执行具体步骤
- **隔离设计** - 每个步骤都是独立单元，有明确的输入输出定义

## 适用场景

- 需要从头创建新的 AI 工作流
- 想要将复杂任务重构为结构化的多步骤工作流
- 需要为 Agent 流程定义清晰的契约和测试用例

## 使用方法

```bash
/claude 创建一个新的工作流，用于...
```

或

```bash
/claude 帮我设计一个 PRD 生成工作流
```

### 创建流程

技能会按以下四个阶段执行：

1. **定位阶段** - 说明创建目标和流程
2. **引导问答** - 收集工作流目标、步骤、路由逻辑、测试用例
3. **确认摘要** - 呈现完整计划等待用户批准
4. **执行创建** - 生成工作流目录结构

## 生成的目录结构

```text
.ai-workflows/<workflow-id>/
  orchestration.md          # 主 Agent 的路由逻辑
  workflow.spec.json        # 工作流元数据
  steps/
    step-01-discovery.md    # 子 Agent 指令
    step-02-processing.md
  fixtures/
    step-01-discovery/
      happy-path/
        prompt.md           # 子 Agent 输入
        expected.md         # 期望输出描述
        assertions.md       # 主 Agent 验证标准
  runs/                     # 执行状态目录
  snapshots/                # 调试快照
```

## 设计原则

### 主 Agent 编排
主 Agent 负责协调、路由和更新全局运行状态，不执行具体业务逻辑。

### 子 Agent 执行
每个工作流步骤必须由子 Agent 执行，确保职责分离。

### 隔离性
每个步骤都是独立单元，有定义的输入输出，便于调试和测试。

### Markdown Fixtures
调试和测试基于嵌套结构的 Markdown 文件，优先使用描述性断言而非严格的 JSON 验证。

## Fixture 结构

每个测试用例包含三个文件：

| 文件 | 说明 |
|------|------|
| `prompt.md` | 发送给子 Agent 的完整提示 |
| `expected.md` | 对期望结果的描述性总结 |
| `assertions.md` | 主 Agent 判断成功的 Markdown 标准 |

## 相关技能

- **execute-ai-workflow** - 执行已创建的工作流
- **debug-ai-workflow** - 调试工作流中的单个步骤

## 示例

```bash
# 创建一个新的代码审查工作流
/claude 创建一个代码审查工作流，包含以下步骤：
1. 分析 PR 变更
2. 识别潜在问题
3. 生成审查意见
```
