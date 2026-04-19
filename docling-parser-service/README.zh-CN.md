# Docling Parser Service

这套 `docling` 解析服务不是只能在当前这台电脑上使用。

只要满足下面几个前提，其他 Windows 机器也可以直接复用：

- 仓库结构保持一致，`frontend/AI-expert-review-paper-system` 与 `.venv` 都在工作区内
- 已安装 `docling-parser-service/requirements.txt` 中的依赖
- 首次运行 `docling` 时允许模型下载
- 如果工作区路径包含中文，服务会自动用 `subst` 创建一个临时 ASCII 盘符别名来绕过 `docling_parse` 的路径兼容问题

## 启动方式

联合启动前端与 `docling`：

```powershell
start-docling-dev.cmd
```

或：

```powershell
npm run dev:all:docling
```

仅启动 `docling` 服务：

```powershell
cd docling-parser-service
python -m docling_parser_service.app
```

默认地址：

```text
http://127.0.0.1:8010
```

## 为什么会看到额外盘符

如果仓库路径里有中文，服务启动时可能会临时出现类似 `W:`、`X:` 的盘符。

这不是新硬盘，也不会额外占用空间，它只是原始目录的另一个入口。资源管理器里显示的容量仍然来自原来的磁盘。

## 当前默认策略

为了让普通笔记本也尽量跑得动，服务默认做了几件事：

- 线程数降到 `1`
- `queue_max_size` 限制为 `2`
- OCR 默认关闭
- 公式增强默认关闭
- 超过阈值的 PDF 会按页分块后再解析
- 图片导出默认开启，解析结果会写到 `paper_bundle/assets/`

其中分块大小默认是 `4` 页，可以按机器情况调整。

## 图片与公式

### 图片

现在 Markdown 会优先导出成引用式图片：

```markdown
![Image](assets/xxx.png)
```

前端会根据 `paperAssetBase` 自动把这些相对路径解析成可访问地址，所以只要 `assets/` 里成功生成了图片，页面就会显示出来。

如果仍然只看到 `<!-- image -->`，通常说明这次解析没有实际导出到图片资源，可以重点检查：

- 是否使用了更新后的 `docling-parser-service`
- 当前运行的服务是否已重启
- `paper_bundle/assets/` 中是否真的生成了图片文件

### 公式

当前默认配置下没有开启 `docling` 的重型公式增强模型，因此公式展示采用“文本兜底”的方式：

- 服务端把 `<!-- formula-not-decoded -->` 替换成 `$$ ... $$`
- 前端把这些块渲染成可见的公式文本卡片

这能保证公式内容至少可读，但不是完整的数学排版引擎效果。

如果后续要追求更像论文阅读器的公式显示，可以继续做两种增强：

- 开启 `DOCLING_PARSER_ENABLE_FORMULAS=true`，尝试让 `docling` 产出更完整的公式文本
- 在前端接入专门的数学渲染器，把 `$$...$$` 进一步渲染成真正的排版公式

## 常用环境变量

```text
DOCLING_PARSER_HOST=127.0.0.1
DOCLING_PARSER_PORT=8010
DOCLING_PARSER_THREADS=1
DOCLING_PARSER_TIMEOUT_SECONDS=120
DOCLING_PARSER_MAX_PAGES=80
DOCLING_PARSER_MAX_FILE_MB=30
DOCLING_PARSER_CHUNK_PAGES=4
DOCLING_PARSER_IMAGE_SCALE=1.0
DOCLING_PARSER_OCR_BATCH_SIZE=1
DOCLING_PARSER_LAYOUT_BATCH_SIZE=1
DOCLING_PARSER_TABLE_BATCH_SIZE=1
DOCLING_PARSER_QUEUE_MAX_SIZE=2
DOCLING_PARSER_ENABLE_OCR=false
DOCLING_PARSER_ENABLE_TABLES=true
DOCLING_PARSER_ENABLE_FORMULAS=false
DOCLING_PARSER_ENABLE_PICTURE_IMAGES=true
DOCLING_PARSER_ENABLE_TABLE_IMAGES=false
```

## 输出结构

每次调用 `/papers/parse` 后都会产出：

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

其中：

- `paper.md` 是前端直接阅读的正文
- `paper_meta.json` 是结构化元信息
- `docling_document.json` 保留了更完整的 `docling` 原始导出
- `assets/` 存放图片等静态资源
