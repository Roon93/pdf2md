import sys
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vendor'))

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTPage, LTTextBox, LTTextLine, LTChar, LTFigure, LTImage, LTRect
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFSyntaxError

from .utils import log_warn, log_error


@dataclass
class Block:
    type: str           # "heading" | "paragraph" | "list_item" | "table" | "image" | "code"
    content: str        # 文本内容
    level: int = 1      # 标题层级(1-3)，列表缩进层级
    ordered: bool = False
    bold: bool = False
    italic: bool = False
    image_path: str = ""
    raw_cells: List[List[str]] = field(default_factory=list)


class PDFParseError(Exception):
    pass


def _get_mode(values: list) -> float:
    """返回列表中出现次数最多的值，列表为空返回 12.0。"""
    if not values:
        return 12.0
    counter = Counter(values)
    return counter.most_common(1)[0][0]


def _get_char_info(text_box) -> tuple:
    """遍历 LTTextBox 中的 LTChar，返回 (avg_size, is_bold, is_italic)。"""
    sizes = []
    is_bold = False
    is_italic = False
    for line in text_box:
        if isinstance(line, LTTextLine):
            for char in line:
                if isinstance(char, LTChar):
                    if char.size > 0:
                        sizes.append(char.size)
                    fontname = char.fontname.lower() if char.fontname else ""
                    if "bold" in fontname:
                        is_bold = True
                    if "italic" in fontname or "oblique" in fontname:
                        is_italic = True
    avg_size = sum(sizes) / len(sizes) if sizes else 12.0
    return avg_size, is_bold, is_italic


def _classify_block(text: str, avg_size: float, is_bold: bool, is_italic: bool, base_size: float) -> Block:
    """根据文本内容和字体信息分类 Block。"""
    stripped = text.lstrip()

    # 检查无序列表
    if stripped.startswith("- ") or stripped.startswith("• ") or stripped.startswith("* "):
        return Block(type="list_item", content=text, ordered=False, bold=is_bold, italic=is_italic)

    # 检查有序列表
    if re.match(r'^\d+\. ', stripped):
        return Block(type="list_item", content=text, ordered=True, bold=is_bold, italic=is_italic)

    # 检查标题（按字体大小）
    if avg_size > base_size * 1.4:
        return Block(type="heading", content=text, level=1, bold=is_bold, italic=is_italic)
    if avg_size > base_size * 1.2:
        return Block(type="heading", content=text, level=2, bold=is_bold, italic=is_italic)
    if avg_size > base_size * 1.05:
        return Block(type="heading", content=text, level=3, bold=is_bold, italic=is_italic)
    if is_bold and avg_size > base_size:
        return Block(type="heading", content=text, level=3, bold=is_bold, italic=is_italic)

    return Block(type="paragraph", content=text, bold=is_bold, italic=is_italic)


def _extract_images(figure, image_output_dir: str, image_counter: list) -> List[Block]:
    """从 LTFigure 中提取图片，保存到 image_output_dir，返回 Block 列表。"""
    result = []
    for item in figure:
        if isinstance(item, LTImage):
            try:
                data = item.stream.get_data()
                if data[:2] == b'\xff\xd8':
                    ext = "jpg"
                elif data[:4] == b'\x89PNG':
                    ext = "png"
                else:
                    ext = "bin"
                filename = f"image_{image_counter[0]:03d}.{ext}"
                image_counter[0] += 1
                out_path = os.path.join(image_output_dir, filename)
                with open(out_path, "wb") as f:
                    f.write(data)
                result.append(Block(type="image", content="", image_path=filename))
            except Exception as e:
                log_warn(f"图片提取失败: {e}")
    return result


def _process_page(page_layout, base_size: float, image_output_dir: str, image_counter: list) -> List[Block]:
    """处理单页，返回 Block 列表。"""
    blocks = []
    for element in page_layout:
        if isinstance(element, LTTextBox):
            text = element.get_text().strip()
            if not text:
                continue
            avg_size, is_bold, is_italic = _get_char_info(element)
            block = _classify_block(text, avg_size, is_bold, is_italic, base_size)
            blocks.append(block)
        elif isinstance(element, LTFigure):
            blocks.extend(_extract_images(element, image_output_dir, image_counter))
        elif isinstance(element, LTRect):
            pass  # 表格识别复杂度高，本版本跳过
    return blocks


def parse_pdf(pdf_path: str, image_output_dir: str) -> List[Block]:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    os.makedirs(image_output_dir, exist_ok=True)
    blocks = []
    image_counter = [0]

    try:
        # 第一遍：收集所有字体大小，计算正文基准字体大小
        font_sizes = []
        for page_layout in extract_pages(pdf_path):
            for element in page_layout:
                if isinstance(element, LTTextBox):
                    for line in element:
                        if isinstance(line, LTTextLine):
                            for char in line:
                                if isinstance(char, LTChar) and char.size > 0:
                                    font_sizes.append(round(char.size, 1))

        # 取众数作为正文基准字体大小
        base_size = _get_mode(font_sizes) if font_sizes else 12.0

        # 第二遍：提取内容
        for page_layout in extract_pages(pdf_path):
            page_blocks = _process_page(page_layout, base_size, image_output_dir, image_counter)
            blocks.extend(page_blocks)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise PDFParseError(f"PDF 解析失败: {e}") from e

    return blocks
