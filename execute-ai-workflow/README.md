# execute-ai-workflow

AI 工作流执行技能 - 用于运行和管理已创建的 AI 工作流。

## 功能特性

- **主 Agent 编排** - 主 Agent 管理路由逻辑、状态转换和子 Agent 调度
- **子 Agent 执行** - 每个步骤由专用子 Agent 执行，职责清晰分离
- **状态管理** - 每个运行的状态记录在独立文件中，支持暂停和恢复
- **完整日志** - 自动记录每个步骤的 prompt 和 response，便于追溯
- **可恢复执行** - 支持从上次成功的步骤继续执行

## 适用场景

- 需要端到端执行已创建的 AI 工作流
- 想要使用 `run_id` 恢复暂停或失败的工作流
- 需要管理复杂的路由和分支逻辑

## 使用方法

### 执行新工作流

```bash
/claude 执行工作流 <workflow-id>
```

### 恢复已存在的工作流

```bash
/claude 继续执行工作流 <workflow-id>，run_id 是 <run-id>
```

## 执行流程

### 阶段 1：初始化/恢复

1. **解析工作流** - 从 `.ai-workflows/<workflow-id>/` 加载工作流
2. **加载编排规则** - 读取 `orchestration.md` 了解路由和契约
3. **确定运行状态**：
   - **新运行**：生成新的 `run_id`，创建目录和 `state.json`
   - **恢复**：加载已存在的 `state.json`，验证未完成

### 阶段 2：执行循环

1. **选择步骤** - 从运行状态识别 `current_step`
2. **准备交接** - 收集所需输入，构建子 Agent 提示
3. **记录 Prompt** - 保存完整 prompt 到 `runs/<workflow-id>/<run-id>/<step-id>/prompt.md`
4. **委托执行** - 调用子 Agent 执行步骤
5. **记录响应** - 保存响应到 `runs/<workflow-id>/<run-id>/<step-id>/response.md`
6. **存储产物** - 保存步骤产生的文件到对应目录
7. **验证** - 主 Agent 根据断言评估响应
8. **更新状态** - 写入步骤输出，确定下一步
9. **循环或停止** - 直到路由表指向 `STOP`

### 阶段 3：完成

1. 总结工作流执行结果
2. 提供最终产物和状态文件路径

## 目录结构（项目根目录）

```text
runs/
  <workflow-id>/
    <run-id>/
      state.json            # 整体运行状态
      <step-01-id>/
        prompt.md           # 发送给子 Agent 的完整提示
        response.md         # 子 Agent 的完整响应
        <other-files>       # 步骤产生的其他文件
      <step-02-id>/
        ...
```

## 状态文件格式

```json
{
  "run_id": "run-2026-04-18T12-00-00Z",
  "workflow_id": "example-workflow",
  "current_step": "step-02-process",
  "completed_steps": ["step-01-init"],
  "step_outputs": {
    "step-01-init": {
      "summary": "..."
    }
  },
  "route_decision": {
    "chosen_next_step": "step-02-process",
    "reason": "entrypoint"
  }
}
```

## 设计原则

### 主 Agent 编排
主 Agent 拥有路由逻辑，选择下一步，准备交接包，更新运行状态。

### 子 Agent 执行
每个步骤必须由子 Agent 执行，主 Agent 不执行业务逻辑。

### 状态管理
进度记录在每个运行的状态文件中 (`runs/<workflow-id>/<run-id>/state.json`)。

### 可恢复性
支持从上次成功的步骤恢复执行。

## 相关技能

- **create-ai-workflow** - 创建新的工作流
- **debug-ai-workflow** - 调试工作流中的单个步骤

## 示例

```bash
# 执行新工作流
/claude 运行 prd-generator 工作流

# 恢复已存在的工作流
/claude 继续执行 code-review 工作流，run_id 是 run-20260418-120000
```
