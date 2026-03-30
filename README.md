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
VITE_API_BASE_URL=http://localhost:8000/api
VITE_USE_LOCAL_PARSER=true
VITE_PARSER_API_BASE_URL=http://127.0.0.1:8000
```

- `VITE_USE_LOCAL_PARSER=true` 时，上传 PDF 会优先调用本仓库内置的解析接口。
- `VITE_USE_MOCK=true` 时，评语和推荐仍使用 mock 数据。

## 目录说明

- `src/`: 前端源码
- `paper-review-system/`: 内嵌的论文解析服务
- `scripts/dev_orchestrator.py`: 一键同时启动前端和解析服务

## 当前接口约定

已经接通的真实接口：

- `POST http://127.0.0.1:8000/papers/parse`

前端预留的后续接口：

- `POST /papers/paper-meta`
- `POST /reviews/generate`
- `POST /recommendations`
- `GET /recommendations/:paperId`
