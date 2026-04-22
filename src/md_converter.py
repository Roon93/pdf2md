from typing import List
from src.pdf_parser import Block


def _apply_inline(content: str, bold: bool, italic: bool) -> str:
    if bold and italic:
        return f"***{content}***"
    if bold:
        return f"**{content}**"
    if italic:
        return f"*{content}*"
    return content


def _render_table(raw_cells: List[List[str]]) -> str:
    if not raw_cells:
        return ""
    header = raw_cells[0]
    rows = raw_cells[1:]
    sep = ["---"] * len(header)
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(sep) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n\n"


def convert_to_markdown(blocks: List[Block]) -> str:
    parts = []
    for block in blocks:
        t = block.type
        if t == "heading":
            prefix = "#" * block.level
            parts.append(f"{prefix} {block.content}\n\n")
        elif t == "paragraph":
            text = _apply_inline(block.content, block.bold, block.italic)
            parts.append(f"{text}\n\n")
        elif t == "list_item":
            text = _apply_inline(block.content, block.bold, block.italic)
            if block.ordered:
                parts.append(f"1. {text}\n")
            else:
                parts.append(f"- {text}\n")
        elif t == "table":
            parts.append(_render_table(block.raw_cells))
        elif t == "image":
            parts.append(f"![]({block.image_path})\n\n")
        elif t == "code":
            parts.append(f"```\n{block.content}\n```\n\n")
    return "".join(parts)
