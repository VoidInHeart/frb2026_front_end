# 论文评分系统前端

基于 `Vue 3 + Vue Router + Vite` 的三页式前端，当前已经内置本地论文解析服务接入：

- 上传页：上传 PDF 后直接调用本仓库内的解析接口
- 评审工作台：左侧展示编译后的 Markdown 预览，右侧展示评语与推荐论文
- 推荐详情页：展示单篇推荐论文详情

## 快速启动

推荐直接双击或执行根目录脚本：

```bash
start-dev.cmd
```

它会同时启动：

- 前端开发服务器：`http://127.0.0.1:5173`
- 本地解析接口：`http://127.0.0.1:8000`

如果你只想启动解析接口：

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

- `VITE_USE_LOCAL_PARSER=true` 时，只要上传了 PDF，就优先调用仓库内的本地解析接口
- `VITE_USE_MOCK=true` 时，评语和推荐仍使用 mock 数据

## 当前仓库结构

- [src](C:\Users\26305\Desktop\frb_project2026\fore_end\src)：前端源码
- [paper-review-system](C:\Users\26305\Desktop\frb_project2026\fore_end\paper-review-system)：精简后的本地论文解析模块
- [scripts/dev_orchestrator.py](C:\Users\26305\Desktop\frb_project2026\fore_end\scripts\dev_orchestrator.py)：一键同时拉起前端和解析接口

## 预留接口

目前真实接通的是本地解析接口：

- `POST http://127.0.0.1:8000/papers/parse`

前端里仍预留了后续接口位置：

- `POST /papers/document-ir`
- `POST /reviews/generate`
- `POST /recommendations`
- `GET /recommendations/:paperId`
