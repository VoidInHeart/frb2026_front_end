# 论文评分系统前端

基于 `Vue 3 + Vue Router + Vite` 的三页式前端：

- 上传页：上传论文或加载示例
- 评审工作台：左侧展示解析后的论文 Markdown，右侧展示评语与推荐论文
- 推荐详情页：展示单篇推荐论文详情

## 运行

```bash
npm install
npm run dev
```

## 环境变量

在项目根目录创建 `.env`：

```bash
VITE_USE_MOCK=true
VITE_API_BASE_URL=http://localhost:8000/api
```

- `VITE_USE_MOCK=true` 时，前端默认读取 `public/mock` 中的示例 `paper.md`、`document_ir.json` 和图片资源
- `VITE_USE_MOCK=false` 时，前端调用真实后端接口

## 预留接口

### 1. 上传并解析论文

`POST {VITE_API_BASE_URL}/papers/parse`

建议表单字段：

- `paper`
- `markdown_file`
- `document_ir_file`
- `image_base_url`

### 2. 发送 document_ir.json

`POST {VITE_API_BASE_URL}/papers/document-ir`

### 3. 生成评语

`POST {VITE_API_BASE_URL}/reviews/generate`

### 4. 推荐论文列表

`POST {VITE_API_BASE_URL}/recommendations`

### 5. 推荐论文详情

`GET {VITE_API_BASE_URL}/recommendations/:paperId`
