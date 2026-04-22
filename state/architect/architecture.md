# pdf2md 架构设计文档

## 项目结构

```
pdf2md/
├── pdf2md.py              # 入口文件，CLI 参数解析
├── vendor/
│   └── pdfminer/          # pdfminer.six 源码（vendor 方式）
├── src/
│   ├── __init__.py
│   ├── pdf_parser.py      # PDF 解析模块
│   ├── md_converter.py    # 结构化内容 → Markdown 转换
│   ├── translator.py      # LLM 翻译模块
│   └── utils.py           # 工具函数
└── state/                 # 工作流状态（不参与运行）
```

## 数据流

```
输入 PDF 文件
    │
    ▼
[pdf_parser.py]
  使用 pdfminer.six 提取文本和布局信息
  输出：List[Block]（结构化内容块列表）
    │
    ▼
[md_converter.py]
  将 Block 列表转换为 Markdown 字符串
  处理标题、列表、表格、粗体/斜体、图片引用
  输出：str（Markdown 文本）
    │
    ├─── 无翻译 ──→ 写入输出文件
    │
    ▼（启用 --translate）
[translator.py]
  按段落调用 LLM API
  将每段原文后插入对应译文
  输出：str（双语对照 Markdown 文本）
    │
    ▼
写入输出文件（.md）
```

## 核心数据结构

### Block（内容块）

```python
@dataclass
class Block:
    type: str        # "heading", "paragraph", "list_item", "table", "image", "code"
    content: str     # 文本内容
    level: int       # 标题层级（1/2/3），列表缩进层级
    ordered: bool    # 列表是否有序
    bold: bool       # 是否粗体
    italic: bool     # 是否斜体
    image_path: str  # 图片路径（type=="image" 时有效）
    raw_cells: list  # 表格单元格（type=="table" 时有效）
```

## 模块说明

### pdf_parser.py

- 通过 `sys.path.insert` 注入 `vendor/` 目录
- 使用 pdfminer.six 的 `PDFPageInterpreter` + `PDFConverter` 提取布局
- 根据字体大小推断标题层级（相对于正文字体大小）
- 根据字体名称推断粗体/斜体（含 "Bold"/"Italic" 字样）
- 提取图片并保存到输出目录，返回相对路径

### md_converter.py

- 将 `List[Block]` 转换为 Markdown 字符串
- 表格使用 GFM 语法（`| col | col |` + 分隔行）
- 图片使用 `![](path)` 语法

### translator.py

- 使用 `urllib.request` 发起 HTTP POST 请求
- 请求格式：OpenAI `/v1/chat/completions`
- 按段落翻译，每次请求翻译一个段落
- 系统提示：自动检测源语言，翻译为中文，只返回译文
- 双语对照：在每个原文段落后插入译文段落

### utils.py

- 路径处理工具
- 日志输出（stderr）

## 错误处理策略

| 场景 | 处理方式 |
|------|----------|
| PDF 文件不存在 | 打印错误信息，退出码 1 |
| PDF 解析失败 | 打印错误信息，退出码 1 |
| LLM API 不可达 | 打印警告，跳过翻译，输出原文 |
| LLM API 返回错误 | 打印警告，该段落保留原文，继续处理 |
| 图片提取失败 | 打印警告，跳过该图片，继续处理 |

## vendor 依赖管理

pdfminer.six 以源码方式放入 `vendor/pdfminer/`：

```bash
# 在有网络的机器上执行
pip download pdfminer.six --no-deps -d /tmp/pkgs
# 解压 wheel 文件，将 pdfminer/ 目录复制到 vendor/
```

运行时注入路径：
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vendor'))
```

pdfminer.six 本身只依赖 Python 标准库（cryptography 是可选依赖，不需要），因此 vendor 方式完全可行。
