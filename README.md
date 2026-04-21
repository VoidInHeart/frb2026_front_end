# 论文评分系统前端

当前仓库包含两部分：

- `Vue 3 + Vue Router + Vite` 前端
- 内嵌的本地论文解析服务 `paper-review-system`

目前已经切换到新的锚点列表解析格式。上传 PDF 后，解析服务会生成：

- `paper_bundle/paper.md`
- `paper_bundle/paper_meta.json`
- `paper_bundle/assets/figures/*`
- `paper_bundle/assets/tables/*`

其中 `paper.md` 包含 `[Page x]`、`[Anchor: ...]`、`[FigureRef: ...]`、`[TableRef: ...]`，前端左侧会按编译后的 Markdown preview 展示；右侧继续展示评语区、评分维度和推荐论文列表。

## 一键启动

在仓库根目录运行：

```bash
start-dev.cmd
```

会同时启动：

- 前端开发服务：`http://127.0.0.1:5173`
- 本地解析接口：`http://127.0.0.1:8000`

如果只想启动解析接口：

```bash
start-parser.cmd
```

## 常用命令

```bash
npm install
npm run dev
npm run dev:parser
npm run dev:all
npm run build
```

## 环境变量

根目录 `.env` 可参考：

```bash
VITE_USE_MOCK=true
VITE_API_BASE_URL=http://10.192.245.241:8000/api
VITE_USE_LOCAL_PARSER=true
VITE_PARSER_API_BASE_URL=http://127.0.0.1:8000
```

- `VITE_USE_MOCK=true` 时，上传页仍可走真实解析，但审查 run、汇总和推荐列表使用 mock 数据。
- `VITE_USE_MOCK=false` 时，前端切到真实的 `/api/runs` 运行态工作流。
- `VITE_USE_LOCAL_PARSER=true` 时，上传 PDF 会优先调用本仓库内置的解析接口 `http://127.0.0.1:8000/papers/parse`。
- `VITE_USE_LOCAL_PARSER=false` 时，PDF 上传会走业务后端的 `POST /api/papers/parse`；如果直接提供 `paper.md` 与 `paper_meta.json`，前端会跳过解析接口，直接创建 review run。

## 非 Mock 联调配置

如果要梳理和验证当前前端“不使用 mock”的真实业务流程，建议至少使用下面这组配置：

```bash
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://10.192.245.241:8000/api
VITE_USE_LOCAL_PARSER=true
VITE_PARSER_API_BASE_URL=http://127.0.0.1:8000
```

常见组合说明：

- 本地解析 + 远端业务后端：保持 `VITE_USE_LOCAL_PARSER=true`，PDF 先走本地 `paper-review-system`，再把 `paper_bundle` 提交到远端 `/api/runs`。
- 业务后端统一处理解析和运行态：设为 `VITE_USE_LOCAL_PARSER=false`，上传和 run 都走 `VITE_API_BASE_URL` 指向的后端。

## 目录说明

- `src/`: 前端源码
- `paper-review-system/`: 内嵌的论文解析服务
- `scripts/dev_orchestrator.py`: 一键同时启动前端和解析服务

## 非 Mock 业务流程

当前前端在 `VITE_USE_MOCK=false` 时，主链路已经不是直接调用零散的 `task1/task2` 页面接口，而是统一走 `run/state/stage` 协议。

### 1. 上传入口

- 上传页支持两种入口：
  - 上传 PDF。
  - 在“高级导入”里同时提供 `paper.md` 与 `paper_meta.json`。
- 当 `VITE_USE_LOCAL_PARSER=true` 且用户上传的是 PDF 时，前端会先请求本地解析服务：
  - `POST {VITE_PARSER_API_BASE_URL}/papers/parse`
- 其他情况里，如果上传的是 PDF，会走业务后端的解析入口：
  - `POST {VITE_API_BASE_URL}/papers/parse`
- 如果在“高级导入”里直接提供 `paper.md` 与 `paper_meta.json`，前端会直接把它们组装成 `paper_bundle`，然后进入：
  - `POST {VITE_API_BASE_URL}/runs`
- 前端会把解析结果统一整理成 submission 对象，核心字段包括：
  - `submissionId`
  - `paperName`
  - `paperMarkdown`
  - `paperAssetBase`
  - `paperMeta`
  - `sourceMode`

### 2. 创建 review run

- 进入 loading 页后，前端会先完成论文解析，再调用：
  - `POST {VITE_API_BASE_URL}/runs`
- 请求体的核心结构是：

```json
{
  "paper_title": "论文标题",
  "paper_bundle": {
    "paper_md": "...",
    "paper_meta": {},
    "assets": {
      "figures_dir": "assets/figures",
      "tables_dir": "assets/tables"
    }
  },
  "runtime_context": {
    "capability_config": {
      "recommendation": {
        "mode": "off"
      }
    }
  }
}
```

- 创建成功后，前端会立即请求：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/state`
- 然后把 `submission`、`runRecord`、`runState` 写入会话状态，进入审查工作区。

### 3. 审查工作区

- 工作区进入时，会先同步一次：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/state`
- 前端根据返回的 `next_stage` 和 `allowed_actions` 决定当前阶段能否操作。
- 只有当“当前显示阶段 === 后端允许的 `next_stage`”时，右侧面板才会显示：
  - `continue`
  - `skip`
  - `abort`
- 用户点击后，前端调用：
  - `POST {VITE_API_BASE_URL}/runs/{runId}/stages/{stageName}`
- 如果后端立即返回了阶段结果，前端直接渲染。
- 如果后端只返回阶段进入运行中，前端会轮询：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/state`
- 当阶段状态变成 `completed` 或 `skipped` 后，前端再读取阶段快照：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/stages/{stageName}`
- 前端当前展示的三段审查分别是：
  - `format`
  - `logic`
  - `innovation`
- 如果某阶段结果被标成高优先级问题，或者后端把 `next_stage` 推进到 `summary`，前端会提前进入汇总页。

### 4. 汇总页

- 进入 summary 页后，前端会先同步一次 run state。
- 如果后端已经允许进入 summary，且本地还没有汇总结果，前端会自动触发：
  - `POST {VITE_API_BASE_URL}/runs/{runId}/stages/summary`
- 随后读取汇总结果：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/summary`
- 推荐列表单独请求：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/recommendations`

### 5. 推荐论文详情

- 在汇总页点击推荐论文后，会跳转到详情页。
- 推荐列表接口是 run 维度的：
  - `GET {VITE_API_BASE_URL}/runs/{runId}/recommendations`
- 但详情页当前仍走单篇详情接口：
  - `GET {VITE_API_BASE_URL}/recommendations/{paperId}`
- 也就是说，列表和详情目前还不是同一套路径协议，这是当前实现里需要注意的一点。

### 6. 前端状态保存

- `reviewSession` 会把以下数据写进 `sessionStorage`，用于刷新后恢复：
  - 当前 submission
  - runRecord
  - runState
  - 各阶段 review 结果
  - summary
  - recommendations

## 当前主工作流接口

非 mock 模式下，当前前端主流程实际会用到这些接口：

- `POST http://127.0.0.1:8000/papers/parse`：本地解析服务，启用 `VITE_USE_LOCAL_PARSER=true` 且上传 PDF 时使用。
- `POST /api/papers/parse`：业务后端解析入口，关闭本地解析且上传 PDF 时使用。
- `POST /api/runs`：创建 run。
- `GET /api/runs/{run_id}/state`：查询 run 状态。
- `POST /api/runs/{run_id}/stages/{stage_name}`：触发阶段执行或人工决策。
- `GET /api/runs/{run_id}/stages/{stage_name}`：读取阶段快照。
- `GET /api/runs/{run_id}/summary`：读取汇总结果。
- `GET /api/runs/{run_id}/recommendations`：读取推荐论文列表。
- `GET /api/recommendations/{paperId}`：读取推荐论文详情。

## 兼容/预留接口

下面这些接口在当前前端代码中仍保留了调用封装，但不属于“非 mock 主工作流”的页面主链路：

- `POST /api/task1/audit`
- `POST /api/task2/audit/`
- `GET /api/task2/get_rules/`
- `POST /api/task2/extract/`
- `POST /api/task2/toggle_rule/`
- `POST /api/papers/paper-meta`
- `POST /api/reviews/generate`
- `POST /api/recommendations`

这些接口更适合看作兼容接口、旁路能力或后续扩展入口，而不是当前页面主业务路径。
