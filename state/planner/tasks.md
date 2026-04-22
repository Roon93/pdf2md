# 任务列表

## task-001: 搭建项目骨架

**依赖：** 无
**文件：**
- `pdf2md/pdf2md.py`（创建，空占位）
- `pdf2md/src/__init__.py`（创建）
- `pdf2md/src/utils.py`（创建）
- `pdf2md/vendor/.gitkeep`（创建，占位）

**描述：**
创建项目目录结构，包括：
- 顶层 `pdf2md.py`（仅写入 `# TODO` 占位）
- `src/__init__.py`（空文件）
- `src/utils.py`：实现两个工具函数：
  - `log_warn(msg: str) -> None`：向 stderr 打印警告信息，格式 `[WARN] {msg}`
  - `log_error(msg: str) -> None`：向 stderr 打印错误信息，格式 `[ERROR] {msg}`
- `vendor/` 目录及 `.gitkeep` 占位文件

**验收：**
- 目录结构与架构文档一致
- `python -c "from src.utils import log_warn, log_error"` 执行无报错
- `log_warn("test")` 在 stderr 输出 `[WARN] test`

---

## task-002: 实现 Block 数据结构

**依赖：** task-001
**文件：**
- `pdf2md/src/pdf_parser.py`（创建）

**描述：**
在 `src/pdf_parser.py` 中定义 `Block` dataclass，字段完全按照接口文档：
- `type: str`
- `content: str`
- `level: int = 1`
- `ordered: bool = False`
- `bold: bool = False`
- `italic: bool = False`
- `image_path: str = ""`
- `raw_cells: List[List[str]] = field(default_factory=list)`

同时定义自定义异常类 `PDFParseError(Exception)`。

此任务只写数据结构，不实现解析逻辑（`parse_pdf` 函数留空或写 `raise NotImplementedError`）。

**验收：**
- `python -c "from src.pdf_parser import Block, PDFParseError"` 无报错
- `Block(type='paragraph', content='hello')` 可正常实例化
- `block.bold` 默认值为 `False`，`block.raw_cells` 默认值为 `[]`

---

## task-003: 实现 PDF 文本提取（pdfminer 集成）

**依赖：** task-002（需要 Block 类和 PDFParseError）
**文件：**
- `pdf2md/src/pdf_parser.py`（修改，添加 pdfminer 导入和基础文本提取逻辑）

**描述：**
在 `src/pdf_parser.py` 中实现 `parse_pdf` 函数的核心骨架：
1. 在文件顶部通过 `sys.path.insert(0, vendor_path)` 注入 vendor 目录
2. 导入 pdfminer 相关模块（`PDFPage`, `PDFPageInterpreter`, `PDFPageAggregator`, `LAParams`, `LTPage`, `LTTextBox` 等）
3. 实现 `parse_pdf(pdf_path, image_output_dir)` 函数：
   - 检查文件存在，否则抛出 `FileNotFoundError`
   - 用 pdfminer 打开 PDF，遍历每页，提取所有 `LTTextBox`
   - 此阶段只返回 `type="paragraph"` 的 Block 列表（不做标题/列表识别）
   - 捕获 pdfminer 异常，转换为 `PDFParseError`

**验收：**
- 对一个真实 PDF 文件调用 `parse_pdf`，返回非空 `List[Block]`
- 所有 Block 的 `type` 为 `"paragraph"`，`content` 非空
- 对不存在的路径抛出 `FileNotFoundError`
- 对损坏的 PDF 抛出 `PDFParseError`

---

## task-004: 实现标题/段落/列表识别

**依赖：** task-003（需要基础文本提取可用）
**文件：**
- `pdf2md/src/pdf_parser.py`（修改，增强 Block 分类逻辑）

**描述：**
在 `parse_pdf` 的文本提取循环中，对每个 `LTTextBox` 进行分类：

1. **正文字体大小基准**：统计所有文本框的字体大小，取众数作为正文基准 `base_size`
2. **标题识别**（基于 `LTChar` 的 `size` 属性）：
   - `size > base_size * 1.4` → `type="heading", level=1`
   - `size > base_size * 1.2` → `type="heading", level=2`
   - `size > base_size * 1.05` → `type="heading", level=3`
   - 字体名含 "Bold" 且 `size > base_size` → 视为标题（level 按大小判断）
3. **粗体/斜体识别**：字体名含 "Bold" → `bold=True`；含 "Italic" 或 "Oblique" → `italic=True`
4. **列表识别**：文本内容以 `- `、`• `、`* ` 开头 → `type="list_item", ordered=False`；以数字+点开头（如 `1. `）→ `type="list_item", ordered=True`

**验收：**
- 对含有标题的 PDF，返回的 Block 列表中存在 `type="heading"` 的块
- H1/H2/H3 层级与 PDF 视觉层级一致（人工核查）
- 以 `- ` 开头的文本被识别为 `type="list_item", ordered=False`
- 以 `1. ` 开头的文本被识别为 `type="list_item", ordered=True`

---

## task-005: 实现表格识别

**依赖：** task-003（需要基础文本提取可用）
**文件：**
- `pdf2md/src/pdf_parser.py`（修改，添加表格识别逻辑）

**描述：**
在 `parse_pdf` 中添加表格识别逻辑：
1. 遍历页面布局中的 `LTRect`（矩形线条），收集所有矩形的坐标
2. 将坐标相近的矩形聚类，识别出表格区域（行列网格）
3. 将落在表格区域内的 `LTTextBox` 按行列坐标归入对应单元格
4. 生成 `Block(type="table", content="", raw_cells=[[...], [...]])` 并从段落列表中移除已归入表格的文本框

注意：表格识别是启发式的，允许误判，但不能崩溃。

**验收：**
- 对含有简单表格的 PDF，返回至少一个 `type="table"` 的 Block
- `raw_cells` 为二维列表，行数和列数与 PDF 表格一致（人工核查）
- 对无表格的 PDF，不返回 `type="table"` 的 Block
- 表格识别失败时打印警告并跳过，不抛出异常

---

## task-006: 实现图片提取

**依赖：** task-003（需要基础文本提取框架）
**文件：**
- `pdf2md/src/pdf_parser.py`（修改，添加图片提取逻辑）

**描述：**
在 `parse_pdf` 中添加图片提取逻辑：
1. 遍历页面布局中的 `LTFigure` 和 `LTImage` 对象
2. 对每个图片对象，使用 `LTImage.stream.get_data()` 获取原始字节
3. 根据图片数据头部判断格式（PNG/JPEG），保存为 `image_001.png` / `image_001.jpg`（序号递增）
4. 保存路径为 `image_output_dir/image_NNN.ext`
5. 生成 `Block(type="image", content="", image_path="image_NNN.ext")`（相对路径）

图片提取失败时调用 `log_warn` 打印警告并跳过。

**验收：**
- 对含有嵌入图片的 PDF，`image_output_dir` 下生成对应图片文件
- 返回的 Block 列表中包含 `type="image"` 的块，`image_path` 指向实际存在的文件
- 图片提取失败时不抛出异常，打印警告后继续处理

---

## task-007: 实现 md_converter.py

**依赖：** task-002（需要 Block 数据结构）
**文件：**
- `pdf2md/src/md_converter.py`（创建）

**描述：**
实现 `convert_to_markdown(blocks: List[Block]) -> str` 函数，按以下规则转换：

| Block.type | 输出 |
|---|---|
| heading level=1 | `# content\n\n` |
| heading level=2 | `## content\n\n` |
| heading level=3 | `### content\n\n` |
| paragraph | `content\n\n` |
| list_item ordered | `1. content\n` |
| list_item unordered | `- content\n` |
| table | GFM 表格（见下） |
| image | `![](image_path)\n\n` |
| code | ` ```\ncontent\n``` \n\n` |

行内格式：
- `bold=True` → `**content**`
- `italic=True` → `*content*`
- `bold=True, italic=True` → `***content***`

GFM 表格格式：从 `raw_cells` 生成，第一行为表头，第二行为分隔行 `| --- |`，后续为数据行。

**验收：**
- `convert_to_markdown([Block(type='heading', content='Title', level=1)])` 返回 `"# Title\n\n"`
- `convert_to_markdown([Block(type='paragraph', content='hello', bold=True)])` 返回 `"**hello**\n\n"`
- 表格 Block 转换为合法的 GFM 表格语法（可用 Markdown 渲染器验证）
- 空列表输入返回空字符串

---

## task-008: 实现 translator.py

**依赖：** task-001（需要 utils.py 的 log_warn）
**文件：**
- `pdf2md/src/translator.py`（创建）

**描述：**
实现两个函数：

**`translate_paragraph(text, api_url, api_key="", model="") -> str`**
- 构造 OpenAI 格式请求体（system prompt + user content）
- 用 `urllib.request.urlopen` 发送 POST 到 `{api_url}/v1/chat/completions`
- 设置 `Content-Type: application/json`，若 `api_key` 非空则设置 `Authorization: Bearer {api_key}`
- 解析响应 JSON，返回 `choices[0].message.content`
- 任何异常（网络错误、JSON 解析失败、KeyError）均捕获，调用 `log_warn` 后返回空字符串

**`translate_markdown(markdown_text, api_url, api_key="", model="") -> str`**
- 按空行分割段落
- 跳过标题行（以 `#` 开头）、代码块（` ``` ` 包裹）、表格行（以 `|` 开头）、图片行（以 `![` 开头）
- 对普通段落调用 `translate_paragraph`，若返回非空则在原文后追加译文段落
- 返回拼接后的双语对照字符串

**验收：**
- `translate_paragraph` 在 API 不可达时返回空字符串，不抛出异常
- `translate_markdown` 对标题行不翻译，直接保留
- 对含有普通段落的 Markdown，返回字符串中每个原文段落后紧跟译文段落（需要可用的 LLM API 才能完整验证）
- 单元测试可 mock `urllib.request.urlopen` 验证请求格式正确

---

## task-009: 实现 pdf2md.py 入口

**依赖：** task-003、task-004、task-005、task-006、task-007、task-008
**文件：**
- `pdf2md/pdf2md.py`（修改，实现完整 CLI）

**描述：**
实现完整的 CLI 入口：

1. 用 `argparse` 解析参数：
   - `input_pdf`（位置参数）
   - `-o / --output`（可选，默认同输入文件名改 `.md` 扩展名）
   - `--translate`（开关）
   - `--api-url`（字符串）
   - `--api-key`（字符串，默认空）
   - `--model`（字符串，默认空）

2. 主流程：
   ```
   检查 input_pdf 存在 → 确定 output_path → 确定 image_output_dir（与 output_path 同目录）
   → parse_pdf(input_pdf, image_output_dir)
   → convert_to_markdown(blocks)
   → 若 --translate：translate_markdown(md_text, api_url, api_key, model)
   → 写入 output_path
   → 打印完成信息到 stdout
   ```

3. 错误处理：
   - `FileNotFoundError` → `log_error` + `sys.exit(1)`
   - `PDFParseError` → `log_error` + `sys.exit(1)`
   - `--translate` 但未提供 `--api-url` → 打印错误 + `sys.exit(1)`

**验收：**
- `python pdf2md.py report.pdf` 生成 `report.md`，内容为合法 Markdown
- `python pdf2md.py report.pdf -o /tmp/out.md` 输出到指定路径
- `python pdf2md.py nonexistent.pdf` 退出码为 1，stderr 有错误信息
- `python pdf2md.py report.pdf --translate`（不带 `--api-url`）退出码为 1

---

## task-010: 编写 vendor 打包说明

**依赖：** 无
**文件：**
- `pdf2md/vendor/README.md`（创建）
- `pdf2md/vendor/fetch_pdfminer.sh`（创建）

**描述：**
编写 vendor 目录的使用说明和打包脚本：

**`vendor/README.md`** 说明：
- vendor 目录用途（存放 pdfminer.six 源码，避免 pip 依赖）
- 如何在有网络的机器上打包（执行 `fetch_pdfminer.sh`）
- 如何将打包结果复制到内网机器
- 运行时路径注入方式

**`vendor/fetch_pdfminer.sh`** 脚本：
```bash
#!/bin/bash
# 在有网络的机器上执行，将 pdfminer 源码下载到 vendor/ 目录
pip download pdfminer.six==20221105 --no-deps -d /tmp/pdfminer_pkg
cd /tmp/pdfminer_pkg
# 解压 wheel（wheel 本质是 zip）
unzip -o pdfminer.six-*.whl -d /tmp/pdfminer_extracted
# 复制 pdfminer 包目录到项目 vendor/
cp -r /tmp/pdfminer_extracted/pdfminer <项目根目录>/vendor/
echo "Done. vendor/pdfminer/ 已就绪。"
```

**验收：**
- `vendor/README.md` 存在，包含完整的操作步骤
- `vendor/fetch_pdfminer.sh` 存在，脚本语法正确（`bash -n` 检查通过）
- 按照说明操作后，`vendor/pdfminer/` 目录存在且包含 `__init__.py`
