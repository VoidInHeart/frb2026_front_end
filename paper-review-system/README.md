# Paper Parser Service

这个目录现在只保留论文解析相关功能，不再包含评审报告、推荐、规则扫描等模块。

## 保留能力

- PDF -> `document_ir.json`
- PDF -> `evidence_ir.json`
- PDF -> `paper.md`
- 自动抽取图片并在 Markdown 中插入图片链接
- 本地 HTTP 解析接口

## 启动方式

在当前目录执行：

```bash
python -m paper_review_system.web_api
```

或：

```bash
paper-review-api
```

默认地址：

`http://127.0.0.1:8000`

## 接口

### 健康检查

`GET /health`

### 解析 PDF

`POST /papers/parse`

表单字段：

- `paper`: PDF 文件

返回字段：

- `submissionId`
- `paperName`
- `paperMarkdown`
- `paperAssetBase`
- `documentIr`
- `artifacts`

## CLI

```bash
paper-review convert path/to/paper.pdf --output-dir outputs
paper-review serve
```
