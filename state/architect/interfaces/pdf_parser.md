# pdf_parser 模块接口

## 职责

使用 pdfminer.six 解析 PDF 文件，提取结构化内容块列表。

## 函数签名

```python
def parse_pdf(pdf_path: str, image_output_dir: str) -> List[Block]:
    """
    解析 PDF 文件，返回结构化内容块列表。

    Args:
        pdf_path: PDF 文件路径
        image_output_dir: 图片输出目录（图片将保存到此目录）

    Returns:
        List[Block]，按页面顺序排列

    Raises:
        FileNotFoundError: PDF 文件不存在
        PDFParseError: PDF 解析失败
    """
```

## Block 数据结构

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Block:
    type: str           # "heading" | "paragraph" | "list_item" | "table" | "image" | "code"
    content: str        # 文本内容（image 类型为空）
    level: int = 1      # 标题层级(1-3)，列表缩进层级(1-N)
    ordered: bool = False   # 列表是否有序
    bold: bool = False
    italic: bool = False
    image_path: str = ""    # 图片相对路径（type=="image" 时有效）
    raw_cells: List[List[str]] = field(default_factory=list)  # 表格数据
```

## 标题识别规则

- 字体大小 > 正文字体大小 * 1.4 → H1
- 字体大小 > 正文字体大小 * 1.2 → H2
- 字体大小 > 正文字体大小 * 1.05 → H3
- 字体名称含 "Bold" 且字体大小 > 正文 → 视为标题

## 依赖

- `vendor/pdfminer`（通过 sys.path 注入）
- Python 标准库：`os`, `sys`
