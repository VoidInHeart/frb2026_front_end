# Paper Parser Service

这个目录现在只保留论文解析能力，不再包含评审报告、推荐、规则扫描等模块。

## 输出格式

解析结果会写入 `paper_bundle/`，结构如下：

```text
paper_bundle/
├─ paper.md
├─ paper_meta.json
└─ assets/
   ├─ figures/
   └─ tables/
```

其中：

- `paper.md` 用于阅读和证据引用，包含页码标记与锚点列表
- `paper_meta.json` 是结构化 sidecar，供前端和后续服务读取
- `assets/figures` 保存图像导出结果
- `assets/tables` 保存表格 CSV 与截图

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
- `paperMeta`
- `artifacts.markdownPath`
- `artifacts.paperMetaPath`
- `artifacts.bundleDir`
- `artifacts.outputDir`

## CLI

```bash
paper-review convert path/to/paper.pdf --output-dir outputs
paper-review serve
```
