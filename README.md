# AI Workflow Foundation

一套基于 **Admission Control（准入控制）** 模型的多步骤 AI 工作流框架。通过主代理（Main Agent）协调、子代理（Sub-Agent）执行、DAG 路由表驱动的方式，实现复杂的、可测试的工作流编排。

## 核心架构理念

### 1. Admission Control 模型

传统的工作流由主代理决定下一步执行什么，而本框架采用 **Admission Control** 模型：

- **主代理是纯执行者**：只负责查看 `active_steps`、派生子代理、提交结果
- **路由逻辑外置**：`routing.json` 文件定义 DAG 准入条件，对主代理隐藏
- **信号驱动**：每个步骤完成时发出 `nextSteps` 信号到 `pending_signals`
- **自动准入扫描**：执行引擎扫描 `routing.json`，满足条件的步骤自动进入 `active_steps`

```
┌─────────────────────────────────────────────────────────────────┐
│                    Main Agent (Executor)                        │
│  - 读取 active_steps                                            │
│  - 派生子代理执行步骤                                           │
│  - 提交结果到执行引擎                                           │
│  - 不计算路由逻辑                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Execution Engine (routing.json 驱动)                │
│  - 接收步骤完成的 nextSteps 信号                                 │
│  - 扫描 routing.json 中的条件集                                  │
│  - OR 逻辑：任一条件集满足即可准入                               │
│  - AND 逻辑：条件集内 depends_on 和 required_inputs 必须同时满足   │
│  - 更新 active_steps                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 全局变量唯一性

所有步骤输出的自定义字段（除 `success`、`nextSteps`、`schema` 外）必须在全局范围内唯一，避免状态碰撞。

### 3. 工作区隔离

每个步骤执行在隔离的目录中：
```
runs/<workflow-id>/<run-id>/<step-id>/
  ├── sub-agent-prompt.md    # 确切的子代理提示
  ├── response.json          # 原始 JSON 输出
  └── <artifacts...>         # 生成的文件
```

## 三个核心 Skill

### create-ai-workflow

**用途**：从 0 开始设计并搭建新的 AI 工作流。

**何时使用**：
- 需要创建一个新的多步骤 AI 工作流
- 需要支持复杂分支、并行执行或汇合（Join）逻辑

**生成内容**：
- `orchestration.md` - 主代理执行合约（仅定义入口步骤）
- `routing.json` - DAG 准入控制路由表
- `workflow.spec.json` - 工作流元数据
- `steps/*.md` - 每个步骤的指令集
- `steps/schemas/*.json` - 输出 JSON Schema
- `fixtures/` - Markdown 测试用例

**核心脚本**：
- `scripts/init_workflow.py` - 脚手架生成

---

### execute-ai-workflow

**用途**：端到端执行 AI 工作流。

**执行流程**：
1. **初始化**：生成唯一 `run-id`，创建 `state.md`，设置入口步骤
2. **执行步骤**：主代理查看 `active_steps`，派生子代理执行
3. **结果提交**：子代理返回 JSON 后，提交到执行引擎
4. **准入扫描**：执行引擎读取 `routing.json`，更新 `active_steps`
5. **循环**：重复直到 `active_steps` 为空

**目录结构**：
```
runs/<workflow-id>/<run-id>/
  ├── state.md              # 状态机（Frontmatter）+ 结果（Body）
  └── <step-id>/
      ├── sub-agent-prompt.md
      ├── response.json
      └── <artifacts...>
```

**核心脚本**：
- `scripts/run_workflow.py` - 执行引擎

---

### debug-ai-workflow

**用途**：隔离调试和测试单个工作流步骤。

**设计原则**：
- **隔离**：一次只调试一个步骤，不影响主执行
- **Markdown Fixtures**：使用人类可读的测试文件
- **合约验证**：确保步骤输出匹配 Schema，正确评估 `success` 和 `nextSteps`

**使用方式**：

1. **CLI 模式**（默认）- 调试单个步骤
   ```bash
   /debug-ai-workflow --workflow <id> --step <id> --test-case <case>
   ```
   示例：
   ```bash
   /debug-ai-workflow --workflow create-prd --step step-02-discovery --test-case happy-path
   ```

2. **Dashboard 模式** - Web UI 交互式调试
   ```bash
   /debug-ai-workflow --dashboard
   ```
   自动打开浏览器，可在 UI 中选择工作流、步骤、测试用例并运行。

**目录结构**：
```
.ai-workflows/<workflow-id>/fixtures/<step-id>/<test-case>/
  ├── prompt.md          # 输入提示
  ├── expected.md        # 期望输出
  └── assertions.md      # 断言标准

debugs/<workflow-id>/<step-id>/<test-case>/<run-id>/
  ├── sub-agent-prompt.md
  ├── response.json
  ├── validation.md      # 验证推理
  └── result.json        # 通过/失败结果
```

---

## 文件契约

### 步骤文件结构 (`steps/<step-id>.md`)

每个步骤必须遵循标准结构：

```markdown
# Step: <step-id>

## Step Goal
<步骤目标>

## Input
- **workDir**: 工作目录路径
- **<其他输入>**: <描述>

## Instructions
<核心执行逻辑>

## Recommend Next Steps
<下一步建议逻辑，返回字符串数组>

## Output
- **JSON Schema**: `steps/schemas/<step-id>.schema.json`
- **Fields**:
  - `success`: (Boolean) 成功标准是否达成
  - `nextSteps`: (Array of Strings) 下一步 ID 数组
  - `<自定义字段>`: (必须全局唯一)

## Success/Failure Criteria
<成功/失败标准>
```

### 路由表结构 (`routing.json`)

```json
{
  "step-01-init": [
    {
      "condition_name": "入口步骤",
      "depends_on": [],
      "required_inputs": {}
    }
  ],
  "step-02-process": [
    {
      "condition_name": "标准顺序路径",
      "depends_on": ["step-01-init"],
      "required_inputs": {
        "step-01-init.success": true
      }
    }
  ]
}
```

### 状态文件结构 (`runs/<workflow-id>/<run-id>/state.md`)

```markdown
---
{
  "workflow_id": "my-workflow",
  "run_id": "run-20260422-120000",
  "status": "running",
  "active_steps": ["step-02-process"],
  "completed_steps": ["step-01-init"],
  "pending_signals": [],
  "step_outputs": {},
  "created_at": "2026-04-22T12:00:00Z",
  "updated_at": "2026-04-22T12:01:00Z"
}
---

# Workflow Run State

## Step Outcomes
<!-- 步骤结果追加到此处 -->
```

## 使用示例

### 创建工作流

```bash
/create-ai-workflow
```

### 执行工作流

```bash
/execute-ai-workflow --workflow <workflow-id>
```

### 调试步骤

```bash
# CLI 模式 - 调试单个步骤
/debug-ai-workflow --workflow create-prd --step step-02-discovery

# Dashboard 模式 - Web UI 交互调试
/debug-ai-workflow --dashboard
```

## 项目结构

```
<project-root>/
├── .ai-workflows/
│   └── <workflow-id>/
│       ├── orchestration.md      # 主代理合约（入口步骤）
│       ├── routing.json          # DAG 准入控制路由表
│       ├── workflow.spec.json    # 元数据
│       ├── steps/
│       │   ├── <step-id>.md      # 步骤指令
│       │   └── schemas/          # JSON Schema
│       └── fixtures/             # 测试用例
│
├── .claude/skills/
│   ├── create-ai-workflow/       # 创建工作流技能
│   ├── execute-ai-workflow/      # 执行工作流技能
│   └── debug-ai-workflow/        # 调试工作流技能
│
└── runs/                         # 执行状态
    └── <workflow-id>/
        └── <run-id>/
            ├── state.md
            └── <step-id>/
```

## 核心设计决策

| 决策 | 传统模型 | Admission Control 模型 |
|------|----------|------------------------|
| 路由逻辑 | 主代理决定下一步 | `routing.json` 驱动，主代理不感知 |
| 下一步建议 | 硬编码序列 | `nextSteps` 信号驱动 |
| 分支/并行 | 复杂条件判断 | OR 逻辑条件集 |
| 汇合（Join） | 手动状态追踪 | AND 逻辑自动汇合 |
| 调试隔离 | 难以隔离 | fixtures + 独立 `debugs/` 目录 |

## 优势

1. **确定性**：路由逻辑在 `routing.json` 中，不依赖 LLM 推理
2. **可测试**：每个步骤有独立的 Markdown fixtures
3. **可扩展**：支持复杂 DAG（分支、并行、汇合）
4. **可审计**：每个步骤的确切提示和输出都有记录
5. **隔离**：每个步骤有独立工作区，避免文件冲突
