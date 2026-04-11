# Development Workflow Rules

> 此文件定义 LLM 开发工作流的强制规则。

## Full Flow (MUST follow, no exceptions)

### feat (新功能)
1. 理解需求，分析影响范围
2. 读取现有代码，理解模式
3. 编写实现代码
4. 验证后端 API（uvicorn 日志 + Swagger）
5. 验证前端渲染（浏览器）
6. 更新 CLAUDE.md（若架构/模块变化）

### fix (缺陷修复)
1. 复现问题，确认症状
2. 定位根因
3. 修复代码
4. 回归验证

## Context Logging (决策记录)

当你做出以下决策时，追加到 `.context/current/branches/<当前分支>/session.log`：

1. **方案选择**：选 A 不选 B 时，记录原因
2. **Bug 发现与修复**：根因 + 修复方法
3. **API/架构决策**：接口设计选择
4. **放弃的方案**：为什么放弃

追加格式：

## <ISO-8601 时间>
**Decision**: <你选择了什么>
**Alternatives**: <被排除的方案>
**Reason**: <为什么>
**Risk**: <潜在风险>
