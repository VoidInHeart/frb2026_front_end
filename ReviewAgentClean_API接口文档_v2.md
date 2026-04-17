# ReviewAgentClean API 接口文档 v2

更新时间：2026-04-16

本文档覆盖运行态网关接口，适用于前后端联调、测试脚本和验收。

## 1. 基础约定

### 1.1 网关与前缀

1. 统一前缀：/api
2. FastAPI 路由实现：src/review_agent/http_api/app.py
3. Django 路由实现：src/review_agent/django_gateway/urls.py + src/review_agent/django_gateway/views.py
4. 两套网关路由与返回结构保持一致，生产环境二选一部署即可。

### 1.2 统一响应包

成功响应：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "ok": false,
  "code": "ERROR_CODE",
  "message": "readable error message",
  "data": {}
}
```

### 1.3 阶段名映射

外部阶段名（前端可见）：

1. format
2. logic
3. innovation
4. summary

内部阶段名（编排器执行）：

1. format -> task2_prefilter
2. logic -> task1
3. innovation -> task2_refine
4. summary -> recommendation_e5

### 1.4 manage.py 启动说明

1. 本项目的 Django 启动入口位于 review-agent-clean/manage.py。
2. 如果终端当前目录在 review-agent-clean 内，可直接执行：python manage.py runserver 0.0.0.0:8000。
3. 如果终端当前目录在父目录（例如 D:/桌面/冯如杯），请执行：python .\\review-agent-clean\\manage.py runserver 0.0.0.0:8000。

## 2. 接口清单

## 2.1 健康检查

- 方法与路径：GET /api/health
- 说明：服务存活检查，不依赖 run_id。

示例响应：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "service": "review-agent-clean-api",
    "version": "v2"
  }
}
```

## 2.2 创建运行

- 方法与路径：POST /api/runs
- 说明：创建一次审查任务，返回 run_id 和当前阶段指针。

请求体：

```json
{
  "paper_title": "string，可选",
  "markdown_text": "string，可选，和 paper_bundle 至少提供一个",
  "paper_meta": {},
  "paper_bundle": {},
  "runtime_context": {}
}
```

成功响应 data 字段：

1. run_id: 运行唯一 ID
2. status: created
3. current_stage: format
4. next_stage: format
5. allowed_actions: ["continue"]
6. accepted_at: 时间戳

常见失败：

1. 400 RUN_INVALID_PAYLOAD：JSON 非法，或 markdown_text 与 paper_bundle 同时缺失。

## 2.3 查询运行状态

- 方法与路径：GET /api/runs/{run_id}/state
- 说明：查询阶段进度、可执行动作和阻塞原因。

成功响应 data 字段：

1. run_id
2. status: created | running | waiting | in_progress | completed | aborted | failed
3. current_stage
4. next_stage
5. progress: 0-100
6. stage_runs: 阶段状态数组
7. stage_statuses: 阶段状态字典
8. allowed_actions: 可操作动作
9. block_reason_code / block_reason_message
10. last_error

常见失败：

1. 404 RUN_NOT_FOUND

## 2.4 执行阶段

- 方法与路径：POST /api/runs/{run_id}/stages/{stage_name}
- 说明：按阶段推进执行，动作由 action 指定。

职责定位：执行接口（会触发编排器实际运行）

请求体：

```json
{
  "action": "continue",
  "operator": "frontend_user",
  "reason": ""
}
```

action 可选值：continue | skip | abort

action 语义

1. continue：允许当前阶段继续执行；阶段执行后进入下一阶段或等待下一次人工动作。
2. skip：跳过当前阶段执行；当前阶段标记 skipped，后续流程按编排策略继续。
3. abort：终止当前 run；run 进入 aborted 终态，不再继续后续阶段。

说明：该接口在执行前会记录一次阶段决策，然后立即开始执行本阶段，属于“决策 + 执行”一体接口。

重要说明：2.4 不是查询接口。它会触发执行并返回本次执行结果；如果只想读取某阶段已落库输出，应调用 2.5（GET /api/runs/{run_id}/stages/{stage_name}）。

成功响应 data 字段：

1. run_id
2. stage_name: 外部阶段名
3. stage_status: completed | skipped | waiting | aborted
4. execution_mode: replay_from_start | checkpoint_resume
5. control_state: 编排器控制状态（可能含 waiting/aborted）
6. result: 当前一次编排执行的完整结果

顺序约束：

1. 若请求阶段不是 next_stage，返回 409 STAGE_NOT_READY。
2. 若 run 已是 completed/aborted/failed，返回 409 RUN_STATE_CONFLICT。

## 2.5 查询阶段快照

- 方法与路径：GET /api/runs/{run_id}/stages/{stage_name}
- 说明：读取某阶段已持久化输出。

成功响应 data 字段：

1. run_id
2. stage_name
3. stage_status
4. stage_output

备注：若阶段被 skip 且没有输出，返回占位结构：

```json
{
  "available": false,
  "reason_code": "STAGE_SKIPPED",
  "warnings": []
}
```

## 2.6 查询最终摘要

- 方法与路径：GET /api/runs/{run_id}/summary
- 说明：读取 result_summary。

成功响应 data 字段：

1. run_id
2. result_summary

result_summary 会做最小规范化：

1. merged_issues 保证为数组
2. warnings 保证为数组

## 2.7 查询推荐论文

- 方法与路径：GET /api/runs/{run_id}/recommendations
- 说明：独立接口，返回 result_summary.recommended_papers。

成功响应 data 字段：

1. implemented: true
2. run_id
3. items: 推荐列表
4. count: 列表长度

## 2.8 记录人工决策

- 方法与路径：POST /api/runs/{run_id}/decisions
- 说明：记录某阶段人工动作，供后续阶段执行读取。

职责定位：仅记录接口（不触发编排执行）

请求体：

```json
{
  "stage_name": "logic",
  "action": "continue",
  "operator": "frontend_user",
  "reason": ""
}
```

action 可选值：continue | skip | abort

说明：该接口只写入 decision_log，不会产出 stage_output，也不会推进阶段状态。

成功响应 data 字段：

1. decision_id
2. run_id
3. stage_name
4. action
5. operator
6. reason
7. created_at

## 2.9 2.4 与 2.8 的区别与前端使用建议

核心区别

1. 2.4 是执行接口：会真正运行阶段逻辑并返回 result。
2. 2.8 是记录接口：只保存人工动作，不执行阶段逻辑。
3. 2.4 适合“点击按钮立即跑”；2.8 适合“先审批、后统一触发执行”。

前端建议用法

1. 常规联调/单步按钮：直接调用 2.4（通常不需要先调 2.8）。
2. 审批流或双人复核：先调 2.8 留痕，再由调度按钮调用 2.4。
3. 需要审计轨迹（谁在何时决定 continue/skip/abort）：保留 2.8 调用。

常见误区

1. 只调 2.8 不调 2.4：阶段不会执行，看不到 stage_output。
2. 连续调 2.8 和 2.4 且 action 不一致：最终以 2.4 本次提交的 action 为准。

## 3. 推荐调用顺序

最小联调链路（必须）

1. POST /api/runs
2. GET /api/runs/{run_id}/state
3. POST /api/runs/{run_id}/stages/format
4. POST /api/runs/{run_id}/stages/logic
5. POST /api/runs/{run_id}/stages/innovation
6. POST /api/runs/{run_id}/stages/summary
7. GET /api/runs/{run_id}/summary
8. GET /api/runs/{run_id}/recommendations

带阶段快照的联调链路（推荐用于前端阶段页/调试）

1. POST /api/runs
2. GET /api/runs/{run_id}/state
3. POST /api/runs/{run_id}/stages/format
4. GET /api/runs/{run_id}/stages/format
5. POST /api/runs/{run_id}/stages/logic
6. GET /api/runs/{run_id}/stages/logic
7. POST /api/runs/{run_id}/stages/innovation
8. GET /api/runs/{run_id}/stages/innovation
9. POST /api/runs/{run_id}/stages/summary
10. GET /api/runs/{run_id}/stages/summary
11. GET /api/runs/{run_id}/summary
12. GET /api/runs/{run_id}/recommendations

说明：GET /api/runs/{run_id}/stages/{stage_name} 已实现，为阶段快照查询接口，不是推进流程的必选步骤。

如果某阶段需要人工闸门，可先调用 POST /api/runs/{run_id}/decisions 再触发下一次阶段执行。

## 4. 常见错误码

1. RUN_INVALID_PAYLOAD：请求体格式非法或必要字段缺失
2. RUN_NOT_FOUND：run_id 不存在
3. STAGE_INVALID：阶段名非法
4. DECISION_INVALID：action 非 continue/skip/abort
5. STAGE_NOT_READY：阶段未到可执行顺序
6. RUN_STATE_CONFLICT：运行已进入终态
7. STAGE_EXECUTION_FAILED：阶段执行参数或上下文不满足
8. INTERNAL_ERROR：服务内部异常

## 5. 与单一 run 入口的关系

编排器只有一个入口函数 run，但 API 仍可分阶段推进，机制如下：

1. 阶段接口在服务层把 action 转换为 manual_gate，并写入 runtime_context。
2. 服务层把历史阶段快照打包成 staged_resume，附在 runtime_context。
3. orchestrator.run 每次都会读取 manual_gate 和 staged_resume。
4. 若 staged_resume 有上游结果，run 会跳过对应阶段的重复执行，直接复用检查点。
5. 若 manual_gate 指示 wait/skip/abort，run 在对应阶段返回 control_state，而不是硬跑到底。
6. 阶段接口据此得到“看起来像分阶段”的执行效果，同时保持 orchestrator 单入口。

这也是 execution_mode 出现 replay_from_start 与 checkpoint_resume 两种取值的原因。

## 6. 全局返回结构与状态码说明

所有网关业务响应默认采用统一包裹结构：

1. ok：布尔值，true 表示业务成功，false 表示业务失败。
2. code：业务码，不等同于 HTTP 状态码。
3. message：可读说明。
4. data：业务载荷；成功时通常是对象，失败时可能为对象或 null。

常见 HTTP 状态码：

1. 200：业务成功。
2. 400：参数或请求体不合法。
3. 404：run_id 不存在。
4. 409：状态冲突（如终态 run、阶段未就绪）。
5. 500：后端内部异常。
6. 422：仅 FastAPI 可能出现（Pydantic 参数校验失败，属于框架层返回）。

## 7. 各接口返回参数字典（按 data 展开）

## 7.1 GET /api/health

成功 data 字段：

1. service：服务标识。
2. version：接口版本号，当前为 v2。

备注：Django 与 FastAPI 的 service 文案可能不同，但字段语义一致。

## 7.2 POST /api/runs

成功 data 字段：

1. run_id：本次任务唯一标识。
2. status：创建状态，通常为 created。
3. current_stage：当前阶段游标，初始为 format。
4. next_stage：下一可执行阶段，初始为 format。
5. allowed_actions：当前允许动作数组，初始通常为 ["continue"]。
6. accepted_at：服务受理时间（UTC ISO 时间串）。

失败场景：

1. RUN_INVALID_PAYLOAD：data 可能为 null，或包含错误上下文。

## 7.3 GET /api/runs/{run_id}/state

成功 data 字段：

1. run_id：任务 ID。
2. status：run 状态。可能值：created、running、waiting、in_progress、completed、aborted、failed。
3. current_stage：当前阶段游标；若全部完成通常显示 summary。
4. next_stage：下一待执行阶段；全部结束时为空字符串。
5. progress：进度百分比，0-100。
6. stage_runs：阶段数组，每项含 stage_name 与 status。
7. stage_statuses：阶段到状态的字典映射。
8. allowed_actions：当前可执行动作数组。
9. block_reason_code：阻塞原因码；无阻塞时为空字符串。
10. block_reason_message：阻塞原因说明；无阻塞时为空字符串。
11. last_error：保留字段，当前实现固定空字符串。

stage_runs / stage_statuses 中 status 常见值：

1. pending：未执行。
2. running：执行中（短暂态）。
3. completed：执行完成。
4. skipped：被跳过。
5. waiting：等待人工动作。
6. aborted：已中止。
7. failed：失败（兼容态，运行中较少出现）。

## 7.4 POST /api/runs/{run_id}/stages/{stage_name}

该接口有两个成功分支。

分支 A：真正执行（阶段未完成且可执行）

1. run_id：任务 ID。
2. stage_name：外部阶段名（format / logic / innovation / summary）。
3. stage_status：本次执行后的阶段状态。常见值：completed、skipped、waiting、aborted。
4. execution_mode：执行模式。可能值：replay_from_start、checkpoint_resume。
5. control_state：控制态对象。若本次不是 waiting/aborted 场景，通常为空对象。
6. result：本次编排完整结果对象（详见第 8 章）。

分支 B：阶段已完成或已跳过（不会重复执行）

1. run_id
2. stage_name
3. stage_status
4. stage_output

备注：分支 B 的返回形态与 2.5 接口一致，本质是直接回放快照。

## 7.5 GET /api/runs/{run_id}/stages/{stage_name}

成功 data 字段：

1. run_id：任务 ID。
2. stage_name：外部阶段名。
3. stage_status：该阶段当前状态。
4. stage_output：阶段输出快照。

特殊占位结构（当 stage_status=skipped 且无输出快照）：

1. available：false。
2. reason_code：STAGE_SKIPPED。
3. warnings：空数组或告警数组。

stage_output 按阶段结构说明（字段释义 + 示例）：

1. 当 stage_name=format 时（内部 task2_prefilter）
2. stage：内部阶段名，固定 task2_prefilter。
3. violations：格式/结构违规列表。
4. risk_signals：风险信号列表（用于升级判断）。
5. term_registry_candidates：术语候选列表。
6. term_registry：术语注册表（去重后）。
7. execution：执行信息。
8. execution.engine：执行引擎，常见 capability 或 fallback。
9. execution.capability_error：能力层错误文本，无错误时为空字符串。
10. token_usage：token 统计。
11. token_usage.prompt_tokens：输入 token。
12. token_usage.completion_tokens：输出 token。

format 阶段示例：

```json
{
  "stage": "task2_prefilter",
  "violations": [
    {
      "rule_id": "R-FMT-001",
      "message": "missing required section: abstract",
      "status": "violated",
      "location": "document",
      "evidence": "Section heading 'abstract' not found.",
      "severity": "major",
      "confidence": 0.92,
      "suggestion": "Add a dedicated 'abstract' section.",
      "evidence_links": []
    }
  ],
  "risk_signals": [
    {
      "type": "format_risk",
      "confidence": 0.69,
      "score": 0.69,
      "reason": "high number of prefilter violations"
    }
  ],
  "term_registry_candidates": [
    {
      "term": "Transformer",
      "normalized": "transformer",
      "aliases": [],
      "kind": "model",
      "first_seen": {"section": "Introduction", "anchor_id": ""},
      "usage_count": 3,
      "source_sections": ["Introduction"],
      "context_snippets": ["...Transformer architecture..."]
    }
  ],
  "term_registry": [
    {
      "term": "Transformer",
      "normalized": "transformer",
      "aliases": [],
      "kind": "model",
      "first_seen": {"section": "Introduction", "anchor_id": ""},
      "usage_count": 3,
      "source_sections": ["Introduction"],
      "context_snippets": ["...Transformer architecture..."]
    }
  ],
  "execution": {"engine": "capability", "capability_error": ""},
  "token_usage": {"prompt_tokens": 532, "completion_tokens": 126}
}
```

13. 当 stage_name=logic 时（内部 task1）
14. stage：内部阶段名，固定 task1。
15. logic_analysis：逻辑审计主体对象。
16. logic_analysis.issues：未解决问题列表（通常与 unresolved_issues 对齐）。
17. logic_analysis.section_issues：分节候选问题。
18. logic_analysis.section_summaries：分节摘要。
19. logic_analysis.resolved_issues：已解决问题。
20. logic_analysis.unresolved_issues：未解决问题。
21. logic_analysis.global_summary：全局仲裁摘要。
22. logic_analysis.prompt_template：使用的 prompt 模板信息。
23. logic_analysis.execution：执行信息。
24. logic_analysis.execution.engine：整体引擎，常见 capability/fallback/mixed。
25. logic_analysis.execution.section_pass_engine：分节轮引擎。
26. logic_analysis.execution.global_pass_engine：全局仲裁轮引擎。
27. logic_analysis.execution.capability_error：错误文本。
28. token_usage：task1 token 统计。

logic 阶段示例：

```json
{
  "stage": "task1",
  "logic_analysis": {
    "issues": [
      {
        "logical_node": "claim_to_metric",
        "analysis": "Section has strong claim wording without explicit metric evidence.",
        "severity": "major",
        "confidence": 0.76,
        "evidence_links": [],
        "section_id": 2,
        "section_title": "Experiments"
      }
    ],
    "section_issues": [],
    "section_summaries": [
      {
        "section_id": 2,
        "section_title": "Experiments",
        "summary": "Experiments: 1 high-severity logic risk(s) need cross-section arbitration.",
        "issue_count": 1,
        "engine": "capability"
      }
    ],
    "resolved_issues": [],
    "unresolved_issues": [
      {
        "logical_node": "claim_to_metric",
        "analysis": "Section has strong claim wording without explicit metric evidence.",
        "severity": "major",
        "confidence": 0.76,
        "evidence_links": [],
        "section_id": 2,
        "section_title": "Experiments"
      }
    ],
    "global_summary": "Global arbitration kept 1 unresolved logic issue(s).",
    "prompt_template": {
      "template_id": "task1_logic_audit_prompt_v1",
      "version": "v1"
    },
    "execution": {
      "engine": "capability",
      "section_pass_engine": "capability",
      "global_pass_engine": "capability",
      "capability_error": ""
    }
  },
  "token_usage": {"prompt_tokens": 1240, "completion_tokens": 311}
}
```

29. 当 stage_name=innovation 时（内部 task2_refine）
30. stage：内部阶段名，固定 task2_refine。
31. violations：创新性/方法论问题列表。
32. innovation_summary：创新审查摘要对象（键名由执行器返回决定）。
33. execution：执行信息（engine、capability_error）。
34. web_search：外部检索元信息数组。
35. external_evidence：外部证据数组（用于先验检索与推荐）。

innovation 阶段示例：

```json
{
  "stage": "task2_refine",
  "violations": [
    {
      "rule_id": "R-REFINE-002",
      "message": "innovation claim lacks comparative support",
      "status": "violated",
      "location": "document",
      "evidence": "Novelty claim exists but no baseline/sota comparison cue detected.",
      "severity": "major",
      "confidence": 0.72,
      "suggestion": "Provide baseline comparison or ablation to support novelty.",
      "evidence_links": []
    }
  ],
  "innovation_summary": {
    "claim_quality": "medium",
    "method_alignment": "medium",
    "reproducibility_risk": "high"
  },
  "execution": {"engine": "fallback", "capability_error": "timeout"},
  "web_search": [
    {
      "query": "transformer novelty baseline",
      "provider": "hybrid",
      "enable_outbound": true,
      "provided_evidence_count": 0,
      "fetched_evidence_count": 3,
      "effective_evidence_count": 3,
      "similar_hits": [],
      "search_error": ""
    }
  ],
  "external_evidence": [
    {
      "title": "Attention Is All You Need",
      "url": "https://arxiv.org/abs/1706.03762",
      "year": 2017,
      "source": "semantic_scholar"
    }
  ]
}
```

36. 当 stage_name=summary 时（内部 recommendation_e5）
37. stage_output 本质为 result_summary 快照。
38. 常见字段：violations、risk_signals、logic_analysis、merged_issues、evidence_links、term_registry、recommended_papers、budget_state、warnings。

summary 阶段示例：

```json
{
  "violations": [],
  "risk_signals": [],
  "logic_analysis": null,
  "merged_issues": [
    {
      "rule_id": "LOGIC-AUDIT-ISSUE",
      "status": "violated",
      "location": "logic_chain",
      "evidence": "argument jump without sufficient support",
      "severity": "major",
      "confidence": 0.81,
      "source_stage": "task1",
      "stage_hits": ["task1"],
      "evidence_refs": ["ev_4b6d0919c5de"]
    }
  ],
  "evidence_links": [
    {
      "evidence_id": "ev_4b6d0919c5de",
      "source": "LOGIC-AUDIT-ISSUE",
      "anchor": "text://issue/1",
      "title": "",
      "label": "text://issue/1",
      "source_stage": "task1",
      "rule_id": "LOGIC-AUDIT-ISSUE",
      "issue_key": "",
      "confidence": 0.81,
      "snippet": "argument jump without sufficient support"
    }
  ],
  "term_registry": [],
  "recommended_papers": [
    {
      "title": "Attention Is All You Need",
      "url": "https://arxiv.org/abs/1706.03762",
      "year": 2017,
      "source": "paper_recommendation",
      "query": "transformer novelty baseline",
      "snippet": "Foundational transformer architecture paper.",
      "citation_count": 120000,
      "retrieved_at": "2026-04-16T09:40:15.000000+00:00"
    }
  ],
  "budget_state": {
    "calls_by_stage": {"task2_prefilter": 1, "task1": 1, "task2_refine": 1},
    "tokens_by_stage": {"task2_prefilter": 658, "task1": 1551, "task2_refine": 438},
    "total_calls": 3,
    "total_tokens": 2647,
    "limits": {
      "max_total_calls": 24,
      "max_total_tokens": 180000,
      "max_tokens_per_call": 14000,
      "max_calls_by_stage": {"task2_prefilter": 10, "task1": 8, "task2_refine": 6}
    }
  },
  "warnings": []
}
```

39. 当阶段尚未执行且没有快照时，stage_output 可能为 {}。

## 7.6 GET /api/runs/{run_id}/summary

成功 data 字段：

1. run_id：任务 ID。
2. result_summary：最终汇总对象（详见第 8.5 节）。

规范化保证：

1. merged_issues 始终为数组。
2. warnings 始终为数组。

备注：若 summary 阶段尚未完成，result_summary 可能为空对象。

## 7.7 GET /api/runs/{run_id}/recommendations

成功 data 字段：

1. implemented：固定 true，表示接口已实现。
2. run_id：任务 ID。
3. items：推荐论文数组（来自 result_summary.recommended_papers）。
4. count：items 数量。

items 单项常见字段（推荐模块标准化后）：

1. title：论文标题。
2. url：论文链接。
3. year：年份（整数或 null）。
4. source：来源（如 stage_external_evidence / paper_recommendation）。
5. query：召回查询词。
6. snippet：摘要片段。
7. citation_count：引用数。
8. retrieved_at：检索时间（若上游提供）。

## 7.8 POST /api/runs/{run_id}/decisions

成功 data 字段：

1. decision_id：决策记录 ID。
2. run_id：任务 ID。
3. stage_name：外部阶段名。
4. action：continue / skip / abort。
5. operator：操作人标识。
6. reason：操作原因。
7. created_at：记录创建时间（UTC ISO 时间串）。

备注：该接口只记录，不执行阶段。

## 8. 2.4 result 深层字段字典（最重要）

## 8.1 result 根对象

1. document_bundle：文档标准化视图。
2. stage_outputs：各阶段输出集合（内部阶段名为 key）。
3. review_tasks：运行时任务列表。
4. escalation_plan：升级计划列表。
5. result_summary：汇总结果。
6. metrics：执行指标。
7. fallback_actions：回退动作列表。
8. control_state：仅在 waiting/aborted 控制态场景出现。

## 8.2 document_bundle 字段

1. doc_id：文档 ID。
2. paper_title：论文标题。
3. markdown_text：论文 Markdown 正文。
4. sections：分节数组。
5. chunks：切块数组。
6. anchors：锚点数组。
7. anchor_map：章节到 anchor_id 的映射。
8. paper_meta：原始元信息。

## 8.3 stage_outputs 字段

key 采用内部阶段名：

1. task2_prefilter（format）
2. task1（logic）
3. task2_refine（innovation）
4. recommendation_e5（summary，主要在阶段快照和最终汇总相关链路出现）

task2_prefilter 常见字段：

1. stage：阶段名。
2. violations：违规列表。
3. risk_signals：风险信号列表。
4. term_registry_candidates：术语候选。
5. term_registry：术语注册表。
6. execution：执行信息（engine、capability_error）。
7. token_usage：token 统计（prompt_tokens、completion_tokens）。

task1 常见字段：

1. stage：阶段名。
2. logic_analysis：逻辑分析对象。
3. token_usage：token 统计。

logic_analysis 常见字段：

1. issues：未解决逻辑问题列表（与 unresolved_issues 对齐）。
2. section_issues：分节候选问题。
3. section_summaries：分节摘要。
4. resolved_issues：已解决问题。
5. unresolved_issues：未解决问题。
6. global_summary：全局仲裁摘要。
7. prompt_template：模板信息（template_id、version）。
8. execution：执行信息（engine、section_pass_engine、global_pass_engine、capability_error）。

task2_refine 常见字段：

1. stage：阶段名。
2. violations：创新性/方法论问题列表。
3. innovation_summary：创新性摘要对象。
4. execution：执行信息（engine、capability_error）。
5. web_search：外部检索元信息数组。
6. external_evidence：外部证据数组。

## 8.4 review_tasks 字段

每项常见字段：

1. task_id：任务 ID。
2. stage：内部阶段名。
3. rule_id：规则 ID。
4. executor：执行器名。
5. applicable_paper_types：适用论文类型。
6. default_scope：默认作用域。
7. target_scope：目标作用域。
8. priority：优先级。
9. reason：调度原因。

## 8.5 escalation_plan 字段

每项常见字段：

1. from_stage：升级来源阶段。
2. to_stage：目标阶段。
3. reason：升级原因码文本。
4. trigger_summary：触发统计摘要。
5. budget_snapshot：预算快照。

## 8.6 result_summary 字段

1. violations：聚合后违规列表（偏 task2 视角）。
2. risk_signals：风险信号。
3. logic_analysis：逻辑分析摘要（可能为 null）。
4. merged_issues：跨阶段去重仲裁后的问题列表。
5. evidence_links：证据回链列表。
6. term_registry：术语注册表。
7. recommended_papers：推荐论文列表。
8. budget_state：预算状态（calls/tokens/limits）。
9. warnings：告警字符串列表。

merged_issues 常见字段：

1. rule_id：规则 ID。
2. status：状态（常见 violated）。
3. location：问题位置。
4. evidence：证据文本。
5. severity：严重度（minor / medium / major / critical）。
6. confidence：仲裁后置信度。
7. confidence_max：候选最大置信度。
8. source_stage：来源阶段（task2_prefilter / task1 / task2_refine / multi_stage）。
9. stage_hits：命中阶段数组。
10. dedup_key：去重指纹。
11. arbitration：仲裁元信息。
12. suggestion：修复建议（存在时）。
13. evidence_links：原始证据链接。
14. evidence_refs：证据 ID 引用数组。

evidence_links（result_summary 层）常见字段：

1. evidence_id：证据唯一 ID。
2. source：证据来源。
3. anchor：证据定位（URL 或锚点）。
4. title：证据标题。
5. label：显示标签。
6. source_stage：来源阶段。
7. rule_id：关联规则 ID。
8. issue_key：关联问题 key。
9. confidence：关联问题置信度。
10. snippet：证据片段。

## 8.7 metrics 字段

1. events：阶段事件数组。
2. total_events：事件总数。
3. total_tokens：累计 token。
4. total_latency_ms：累计耗时。
5. success_events：成功事件数。
6. failed_events：失败事件数。

events 单项字段：

1. timestamp
2. stage
3. task_id
4. rule_id
5. executor
6. ok
7. used_tokens
8. latency_ms
9. error_code
10. note

## 8.8 fallback_actions 字段

每项常见字段：

1. stage：发生回退的阶段。
2. task_id：任务 ID。
3. action：回退动作（manual_review / fallback / wait / skip / abort）。
4. reason_code：原因码。
5. reason：原因说明。
6. executor：触发执行器（存在时）。

## 8.9 control_state 字段（可选）

仅在控制态结果中出现，常见字段：

1. status：waiting 或 aborted。
2. pending_stage：等待或中止涉及的阶段。
3. allowed_actions：允许动作数组。
4. mode：当前固定为 manual_gate。

## 9. 错误码与 data 字段字典

1. RUN_INVALID_PAYLOAD：请求体非法。
2. RUN_NOT_FOUND：run 不存在。
3. STAGE_INVALID：阶段名非法。
4. DECISION_INVALID：action 非 continue/skip/abort，或决策参数不合法。
5. STAGE_NOT_READY：阶段顺序不合法。
6. RUN_STATE_CONFLICT：run 已处于终态，不能继续推进。
7. STAGE_EXECUTION_FAILED：阶段执行入参或上下文不满足。
8. INTERNAL_ERROR：后端未捕获异常。

error.data 常见形态：

1. null：仅返回 code/message。
2. {run_id, status}：终态冲突时常见。
3. {run_id, requested_stage, next_stage, allowed_actions}：阶段未就绪时常见。

## 10. 前端落地建议（类型定义）

1. 把 2.4 成功响应定义为联合类型：执行结果分支 | 快照分支。
2. 对 result、stage_output、result_summary 使用“固定字段 + 扩展字段”策略，允许后端透传新字段。
3. 对 warnings、merged_issues、recommended_papers 等数组字段做空数组兜底。
4. FastAPI 场景额外处理 422（框架校验错误），不要只按统一业务包解析。

## 11. 各接口示范返回样例

说明：以下为示例数据，用于帮助前端理解字段形态；真实值以运行时返回为准。

### 11.1 GET /api/health

成功示例：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "service": "review-agent-clean-api",
    "version": "v2"
  }
}
```

### 11.2 POST /api/runs

成功示例：

```json
{
  "ok": true,
  "code": "RUN_ACCEPTED",
  "message": "run accepted",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "status": "created",
    "current_stage": "format",
    "next_stage": "format",
    "allowed_actions": ["continue"],
    "accepted_at": "2026-04-16T09:33:21.102301+00:00"
  }
}
```

失败示例（缺少 markdown_text 与 paper_bundle）：

```json
{
  "ok": false,
  "code": "RUN_INVALID_PAYLOAD",
  "message": "markdown_text or paper_bundle is required",
  "data": null
}
```

### 11.3 GET /api/runs/{run_id}/state

成功示例：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "status": "in_progress",
    "current_stage": "logic",
    "next_stage": "logic",
    "progress": 25,
    "stage_runs": [
      {"stage_name": "format", "status": "completed"},
      {"stage_name": "logic", "status": "pending"},
      {"stage_name": "innovation", "status": "pending"},
      {"stage_name": "summary", "status": "pending"}
    ],
    "stage_statuses": {
      "format": "completed",
      "logic": "pending",
      "innovation": "pending",
      "summary": "pending"
    },
    "allowed_actions": ["continue"],
    "block_reason_code": "",
    "block_reason_message": "",
    "last_error": ""
  }
}
```

失败示例（run 不存在）：

```json
{
  "ok": false,
  "code": "RUN_NOT_FOUND",
  "message": "run not found",
  "data": null
}
```

### 11.4 POST /api/runs/{run_id}/stages/{stage_name}

成功示例 A（正常执行分支）：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "stage_name": "logic",
    "stage_status": "completed",
    "execution_mode": "checkpoint_resume",
    "control_state": {},
    "result": {
      "document_bundle": {
        "doc_id": "doc_77c9",
        "paper_title": "Demo Paper",
        "sections": [],
        "chunks": [],
        "anchors": [],
        "anchor_map": {},
        "paper_meta": {}
      },
      "stage_outputs": {
        "task2_prefilter": {
          "stage": "task2_prefilter",
          "violations": [],
          "risk_signals": []
        },
        "task1": {
          "stage": "task1",
          "logic_analysis": {
            "issues": [],
            "global_summary": "No cross-section logic conflict was detected.",
            "execution": {"engine": "capability"}
          },
          "token_usage": {"prompt_tokens": 1240, "completion_tokens": 311}
        },
        "task2_refine": {
          "stage": "task2_refine",
          "violations": []
        }
      },
      "review_tasks": [],
      "escalation_plan": [],
      "result_summary": {
        "violations": [],
        "risk_signals": [],
        "logic_analysis": null,
        "merged_issues": [],
        "evidence_links": [],
        "term_registry": [],
        "recommended_papers": [],
        "budget_state": {
          "calls_by_stage": {"task2_prefilter": 1, "task1": 1, "task2_refine": 0},
          "tokens_by_stage": {"task2_prefilter": 0, "task1": 1551, "task2_refine": 0},
          "total_calls": 2,
          "total_tokens": 1551,
          "limits": {
            "max_total_calls": 24,
            "max_total_tokens": 180000,
            "max_tokens_per_call": 14000,
            "max_calls_by_stage": {"task2_prefilter": 10, "task1": 8, "task2_refine": 6}
          }
        },
        "warnings": []
      },
      "metrics": {
        "events": [],
        "total_events": 0,
        "total_tokens": 0,
        "total_latency_ms": 0,
        "success_events": 0,
        "failed_events": 0
      },
      "fallback_actions": []
    }
  }
}
```

成功示例 B（阶段已完成，返回快照分支）：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "stage_name": "format",
    "stage_status": "completed",
    "stage_output": {
      "stage": "task2_prefilter",
      "violations": [],
      "risk_signals": [],
      "execution": {"engine": "capability"},
      "token_usage": {"prompt_tokens": 532, "completion_tokens": 126}
    }
  }
}
```

失败示例（阶段未就绪）：

```json
{
  "ok": false,
  "code": "STAGE_NOT_READY",
  "message": "requested stage is not allowed now",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "requested_stage": "innovation",
    "next_stage": "logic",
    "allowed_actions": ["continue"]
  }
}
```

### 11.5 GET /api/runs/{run_id}/stages/{stage_name}

成功示例：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "stage_name": "innovation",
    "stage_status": "skipped",
    "stage_output": {
      "available": false,
      "reason_code": "STAGE_SKIPPED",
      "warnings": []
    }
  }
}
```

### 11.6 GET /api/runs/{run_id}/summary

成功示例：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "result_summary": {
      "violations": [],
      "risk_signals": [],
      "logic_analysis": null,
      "merged_issues": [
        {
          "rule_id": "LOGIC-AUDIT-ISSUE",
          "status": "violated",
          "location": "logic_chain",
          "evidence": "argument jump without sufficient support",
          "severity": "major",
          "confidence": 0.81,
          "source_stage": "task1",
          "stage_hits": ["task1"],
          "evidence_refs": ["ev_4b6d0919c5de"]
        }
      ],
      "evidence_links": [
        {
          "evidence_id": "ev_4b6d0919c5de",
          "source": "LOGIC-AUDIT-ISSUE",
          "anchor": "text://issue/1",
          "title": "",
          "label": "text://issue/1",
          "source_stage": "task1",
          "rule_id": "LOGIC-AUDIT-ISSUE",
          "issue_key": "",
          "confidence": 0.81,
          "snippet": "argument jump without sufficient support"
        }
      ],
      "term_registry": [],
      "recommended_papers": [],
      "budget_state": {
        "calls_by_stage": {"task2_prefilter": 1, "task1": 1, "task2_refine": 0},
        "tokens_by_stage": {"task2_prefilter": 658, "task1": 1551, "task2_refine": 0},
        "total_calls": 2,
        "total_tokens": 2209,
        "limits": {
          "max_total_calls": 24,
          "max_total_tokens": 180000,
          "max_tokens_per_call": 14000,
          "max_calls_by_stage": {"task2_prefilter": 10, "task1": 8, "task2_refine": 6}
        }
      },
      "warnings": []
    }
  }
}
```

### 11.7 GET /api/runs/{run_id}/recommendations

成功示例：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "implemented": true,
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "items": [
      {
        "title": "Attention Is All You Need",
        "url": "https://arxiv.org/abs/1706.03762",
        "year": 2017,
        "source": "paper_recommendation",
        "query": "transformer novelty baseline",
        "snippet": "Foundational transformer architecture paper.",
        "citation_count": 120000,
        "retrieved_at": "2026-04-16T09:40:15.000000+00:00"
      }
    ],
    "count": 1
  }
}
```

### 11.8 POST /api/runs/{run_id}/decisions

成功示例：

```json
{
  "ok": true,
  "code": "OK",
  "message": "success",
  "data": {
    "decision_id": "d1f6a47a-f2f8-4cfd-9b84-2f9714c7dd64",
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "stage_name": "logic",
    "action": "continue",
    "operator": "frontend_user",
    "reason": "reviewer approved",
    "created_at": "2026-04-16T09:37:10.008201+00:00"
  }
}
```

失败示例（action 非法）：

```json
{
  "ok": false,
  "code": "DECISION_INVALID",
  "message": "action must be continue/skip/abort",
  "data": null
}
```

### 11.9 通用终态冲突错误示例（409）

```json
{
  "ok": false,
  "code": "RUN_STATE_CONFLICT",
  "message": "run is in terminal status",
  "data": {
    "run_id": "0b30f8f7-35b7-4a3f-b24d-54adac78b6d6",
    "status": "completed"
  }
}
```
