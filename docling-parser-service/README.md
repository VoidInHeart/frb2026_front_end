# Docling Parser Service

一个独立于现有 `paper-review-system` 的轻量 `Docling` 解析服务。

目标：

- 不删除、不替换当前解析服务
- 在笔记本上尽可能可运行
- 接口尽量兼容现有前端使用方式

## 特性

- 提供 `GET /health`
- 提供 `POST /papers/parse`
- 输出兼容当前前端的字段：
  - `submissionId`
  - `paperName`
  - `paperMarkdown`
  - `paperAssetBase`
  - `paperMeta`
  - `artifacts.*`
- 默认采用偏轻量配置：
  - 默认关闭 OCR
  - 默认关闭公式增强
  - 默认关闭图片描述和图片分类
  - 默认关闭远程服务
  - 默认强制使用 PDF 内嵌文本层
  - 默认限制 CPU 线程数

## 推荐环境

- Python 3.10+
- RAM 16GB
- GPU 非必须

## 安装

在本目录执行：

```bash
pip install -r requirements.txt
```

如果 `docling` 首次运行需要下载模型，请保持网络可用一次。后续可离线运行。

## 启动

```bash
python -m docling_parser_service.app
```

默认地址：

`http://127.0.0.1:8010`

## 可调环境变量

- `DOCLING_PARSER_HOST`
- `DOCLING_PARSER_PORT`
- `DOCLING_PARSER_THREADS`
- `DOCLING_PARSER_TIMEOUT_SECONDS`
- `DOCLING_PARSER_MAX_PAGES`
- `DOCLING_PARSER_MAX_FILE_MB`
- `DOCLING_PARSER_ENABLE_OCR`
- `DOCLING_PARSER_ENABLE_TABLES`
- `DOCLING_PARSER_ENABLE_FORMULAS`
- `DOCLING_PARSER_ENABLE_PICTURE_IMAGES`
- `DOCLING_PARSER_ENABLE_TABLE_IMAGES`

建议笔记本默认值：

- OCR: `false`
- formulas: `false`
- picture_images: `false`
- table_images: `false`
- threads: `4`

## 输出结构

每次请求会写入：

```text
outputs/api_runs/<submission_id>/
├─ input/
│  └─ xxx.pdf
└─ paper_bundle/
   ├─ paper.md
   ├─ paper_meta.json
   ├─ docling_document.json
   └─ assets/
```

## 和现有服务的关系

- 当前旧服务：`paper-review-system`
- 当前新服务：`docling-parser-service`

两者可以并存，互不影响。
