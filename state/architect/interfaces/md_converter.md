# md_converter 模块接口

## 职责

将结构化 Block 列表转换为 Markdown 字符串。

## 函数签名

```python
def convert_to_markdown(blocks: List[Block]) -> str:
    """
    将 Block 列表转换为 Markdown 字符串。

    Args:
        blocks: parse_pdf 返回的内容块列表

    Returns:
        Markdown 格式字符串
    """
```

## 转换规则

| Block.type | Markdown 输出 |
|------------|---------------|
| heading (level=1) | `# content` |
| heading (level=2) | `## content` |
| heading (level=3) | `### content` |
| paragraph | `content\n\n` |
| list_item (ordered) | `1. content` |
| list_item (unordered) | `- content` |
| table | GFM 表格语法 |
| image | `![](image_path)` |
| code | ` ```\ncontent\n``` ` |

## 行内格式

- `bold=True` → `**content**`
- `italic=True` → `*content*`
- `bold=True, italic=True` → `***content***`

## 依赖

- Python 标准库：`typing`
- `src/pdf_parser.py`（Block 数据结构）
