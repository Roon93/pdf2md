import sys
import os
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vendor'))


def _get_tools_dir() -> str:
    """返回 tools 目录的绝对路径。"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools')


def _find_binary(name: str) -> Optional[str]:
    """在 tools/usr/bin/ 中查找可执行文件，找不到则回退到 PATH 中的同名工具。"""
    tools_bin = os.path.join(_get_tools_dir(), 'usr', 'bin')
    bundled = os.path.join(tools_bin, name)
    if os.path.isfile(bundled) and os.access(bundled, os.X_OK):
        return bundled
    # 回退：找系统 PATH 中的同名工具
    import shutil
    return shutil.which(name)

from pdfminer.high_level import extract_pages
from pdfminer.layout import (
    LTPage, LTTextBox, LTTextLine, LTChar, LTFigure, LTImage,
    LTRect, LTCurve, LTLine,
)
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFSyntaxError

from .utils import log_warn, log_error


# ─── 数据结构 ────────────────────────────────────────────────

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


# ─── 工具函数 ────────────────────────────────────────────────

def _get_mode(values: list) -> float:
    if not values:
        return 12.0
    counter = Counter(values)
    return counter.most_common(1)[0][0]


def _get_char_info(text_box) -> tuple:
    sizes = []
    is_bold = False
    is_italic = False
    for line in text_box:
        if isinstance(line, LTTextLine):
            for char in line:
                if isinstance(char, LTChar):
                    if char.size > 0:
                        sizes.append(char.size)
                    fname = char.fontname.lower() if char.fontname else ""
                    if "bold" in fname:
                        is_bold = True
                    if "italic" in fname or "oblique" in fname:
                        is_italic = True
    avg_size = sum(sizes) / len(sizes) if sizes else 12.0
    return avg_size, is_bold, is_italic


def _classify_block(text: str, avg_size: float, is_bold: bool, is_italic: bool,
                   base_size: float) -> Block:
    stripped = text.lstrip()

    # 列表
    if stripped.startswith("- ") or stripped.startswith("• ") or stripped.startswith("* "):
        return Block(type="list_item", content=text, ordered=False,
                     bold=is_bold, italic=is_italic)
    if re.match(r'^\d+\. ', stripped):
        return Block(type="list_item", content=text, ordered=True,
                     bold=is_bold, italic=is_italic)

    # 标题
    if avg_size > base_size * 1.4:
        return Block(type="heading", content=text, level=1,
                     bold=is_bold, italic=is_italic)
    if avg_size > base_size * 1.2:
        return Block(type="heading", content=text, level=2,
                     bold=is_bold, italic=is_italic)
    if avg_size > base_size * 1.05:
        return Block(type="heading", content=text, level=3,
                     bold=is_bold, italic=is_italic)
    if is_bold and avg_size > base_size:
        return Block(type="heading", content=text, level=3,
                     bold=is_bold, italic=is_italic)

    return Block(type="paragraph", content=text, bold=is_bold, italic=is_italic)


# ─── 图片提取 ────────────────────────────────────────────────

def _extract_images(figure, image_output_dir: str,
                   image_counter: list) -> List[Block]:
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
                    # 无法识别的位图数据，跳过（避免生成无意义的 .bin 文件）
                    log_warn(f"跳过无法识别的嵌入图片数据（格式未知）")
                    continue
                filename = f"image_{image_counter[0]:03d}.{ext}"
                image_counter[0] += 1
                out_path = os.path.join(image_output_dir, filename)
                with open(out_path, "wb") as f:
                    f.write(data)
                result.append(Block(type="image", content="", image_path=filename))
            except Exception as e:
                log_warn(f"图片提取失败: {e}")
    return result


# ─── 表格识别（启发式坐标重建）───────────────────────────────

def _bbox(element) -> Tuple[float, float, float, float]:
    """返回 (x0, y0, x1, y1)。"""
    return (element.x0, element.y0, element.x1, element.y1)


def _h_lines(rects, tol=3.0) -> List[float]:
    """从矩形列表提取水平线 Y 坐标（去重）。"""
    ys: Set[float] = set()
    for r in rects:
        if abs(r.y0 - r.y1) < tol:       # 扁矩形 = 水平线
            ys.add(round(r.y0, 1))
    return sorted(ys)


def _v_lines(rects, tol=3.0) -> List[float]:
    """从矩形列表提取垂直线 X 坐标（去重）。"""
    xs: Set[float] = set()
    for r in rects:
        if abs(r.x0 - r.x1) < tol:       # 窄矩形 = 垂直线
            xs.add(round(r.x0, 1))
    return sorted(xs)


def _cells_in_grid(text_boxes: List[LTTextBox],
                   hYs: List[float], vXs: List[float]) -> List[List[str]]:
    """
    将 text_boxes 分配到 (rows x cols) 网格单元格。
    返回二维列表 raw_cells。
    """
    if not hYs or not vXs:
        return []

    n_rows = len(hYs) - 1
    n_cols = len(vXs) - 1
    if n_rows <= 0 or n_cols <= 0:
        return []

    # 初始化空网格
    grid: List[List[Optional[str]]] = [
        [None] * n_cols for _ in range(n_rows)
    ]

    for tb in text_boxes:
        cx = (tb.x0 + tb.x1) / 2.0
        cy = (tb.y0 + tb.y1) / 2.0
        for ri, y_bot in enumerate(hYs[:-1]):
            if cy <= y_bot:
                continue
            for ci, x_left in enumerate(vXs[:-1]):
                if cx >= x_left:
                    continue
                # 找到所在单元格
                if grid[ri][ci] is None:
                    grid[ri][ci] = tb.get_text().strip()
                else:
                    grid[ri][ci] += " " + tb.get_text().strip()
                break
            break

    # None 替换为空字符串
    return [[cell if cell else "" for cell in row] for row in grid]


def _recognize_table(page_elements, base_size: float) -> Tuple[Optional[Block], List[LTTextBox]]:
    """
    扫描页面中的 LTRect/LTLine，尝试识别表格区域。
    返回 (Block 或 None, 已归入表格的 TextBox 列表)。
    """
    rects = []
    for el in page_elements:
        if isinstance(el, LTRect):
            rects.append(el)
        elif isinstance(el, LTCurve) or isinstance(el, LTLine):
            # 将曲线/线条视为同尺寸矩形
            rects.append(el)

    if len(rects) < 4:
        return None, []

    hYs = _h_lines(rects)
    vXs = _v_lines(rects)

    # 至少 2 行 2 列才视为表格
    if len(hYs) < 3 or len(vXs) < 3:
        return None, []

    # 收集所有 TextBox，检查是否有多个落在网格内
    text_boxes = [el for el in page_elements if isinstance(el, LTTextBox)]
    if len(text_boxes) < 2:
        return None, []

    raw_cells = _cells_in_grid(text_boxes, hYs, vXs)
    rows_with_content = [row for row in raw_cells if any(cell for cell in row)]

    # 至少 2 行有内容才视为表格
    if len(rows_with_content) < 2:
        return None, []

    # 过滤掉已被归入表格的 TextBox
    used_boxes = []
    for tb in text_boxes:
        cx = (tb.x0 + tb.x1) / 2.0
        cy = (tb.y0 + tb.y1) / 2.0
        for ri in range(len(hYs) - 1):
            for ci in range(len(vXs) - 1):
                if (hYs[ri] >= cy > hYs[ri + 1] and
                        vXs[ci] <= cx < vXs[ci + 1]):
                    used_boxes.append(tb)

    block = Block(type="table", content="", level=1,
                  raw_cells=raw_cells)
    return block, used_boxes


# ─── 矢量图提取（通过 pdftoppm / ghostscript）───────────────

def _render_vector_figure(pdf_path: str, page_idx: int,
                          figure, image_output_dir: str,
                          image_counter: list) -> Optional[Block]:
    """
    将 LTFigure 区域渲染为 PNG。
    使用 bbox 裁剪页面，只保留该 figure 区域。
    """
    bbox = _bbox(figure)
    x0, y0, x1, y1 = bbox
    if x1 <= x0 or y1 <= y0:
        return None

    filename = f"image_{image_counter[0]:03d}.png"
    image_counter[0] += 1
    out_path = os.path.join(image_output_dir, filename)

    # 尝试 pdftoppm（poppler）
    try:
        pdftoppm = _find_binary("pdftoppm")
        cmd = [
            pdftoppm,
            "-f", str(page_idx + 1),
            "-l", str(page_idx + 1),
            "-r", "150",
            "-cropbox",
            "-x", str(int(x0)),
            "-y", str(int(y0)),
            "-W", str(int(x1 - x0)),
            "-H", str(int(y1 - y0)),
            pdf_path,
            out_path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
        if result.returncode == 0 and os.path.exists(out_path + "-1.png"):
            # pdftoppm 输出为 image-1.png / image-2.png ...
            generated = out_path + "-1.png"
            if os.path.exists(generated):
                os.rename(generated, out_path)
            return Block(type="image", content="", image_path=filename)
    except FileNotFoundError:
        pass
    except Exception as e:
        log_warn(f"pdftoppm 失败: {e}")

    # 回退：pdftocairo
    try:
        pdftocairo = _find_binary("pdftocairo")
        cmd = [
            pdftocairo,
            "-f", str(page_idx + 1),
            "-l", str(page_idx + 1),
            "-r", "150",
            "-cropbox",
            "-x", str(int(x0)),
            "-y", str(int(y0)),
            "-W", str(int(x1 - x0)),
            "-H", str(int(y1 - y0)),
            "-png",
            pdf_path,
            out_path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
        if result.returncode == 0 and os.path.exists(out_path + "-1.png"):
            generated = out_path + "-1.png"
            if os.path.exists(generated):
                os.rename(generated, out_path)
            return Block(type="image", content="", image_path=filename)
    except FileNotFoundError:
        pass
    except Exception as e:
        log_warn(f"pdftocairo 失败: {e}")

    return None


# ─── 页面处理 ────────────────────────────────────────────────

def _process_page(page_layout, page_idx: int, base_size: float,
                  pdf_path: str, image_output_dir: str,
                  image_counter: list) -> List[Block]:
    blocks = []
    page_elements = list(page_layout)

    # ── 表格识别（优先，消耗 LTRect）─────────────────────────
    table_block, used_text_boxes = _recognize_table(page_elements, base_size)
    if table_block is not None:
        blocks.append(table_block)

    # ── 文本块（排除已归入表格的）─────────────────────────
    used_ids = {id(tb) for tb in used_text_boxes}
    for element in page_elements:
        if isinstance(element, LTTextBox):
            if id(element) in used_ids:
                continue
            text = element.get_text().strip()
            if not text:
                continue
            avg_size, is_bold, is_italic = _get_char_info(element)
            block = _classify_block(text, avg_size, is_bold, is_italic, base_size)
            blocks.append(block)

        # ── 嵌入位图（LTImage）─────────────────────────────
        elif isinstance(element, LTFigure):
            img_blocks = _extract_images(element, image_output_dir, image_counter)
            if img_blocks:
                blocks.extend(img_blocks)
            else:
                # 没有位图 → 可能是矢量图（流程图/线条图）
                # 检查是否含 LTCurve / LTLine
                has_vector = any(
                    isinstance(c, (LTCurve, LTLine, LTRect))
                    for c in element
                )
                if has_vector:
                    vb = _render_vector_figure(
                        pdf_path, page_idx, element,
                        image_output_dir, image_counter
                    )
                    if vb is not None:
                        blocks.append(vb)

    return blocks


# ─── 主入口 ────────────────────────────────────────────────

def parse_pdf(pdf_path: str, image_output_dir: str) -> List[Block]:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    os.makedirs(image_output_dir, exist_ok=True)
    blocks = []
    image_counter = [0]

    try:
        # 第一遍：收集字体大小基准
        font_sizes = []
        for page_layout in extract_pages(pdf_path):
            for element in page_layout:
                if isinstance(element, LTTextBox):
                    for line in element:
                        if isinstance(line, LTTextLine):
                            for char in line:
                                if isinstance(char, LTChar) and char.size > 0:
                                    font_sizes.append(round(char.size, 1))

        base_size = _get_mode(font_sizes) if font_sizes else 12.0

        # 第二遍：提取内容（同时获取页码）
        pages = list(extract_pages(pdf_path))
        for page_idx, page_layout in enumerate(pages):
            page_blocks = _process_page(
                page_layout, page_idx, base_size,
                pdf_path, image_output_dir, image_counter
            )
            blocks.extend(page_blocks)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise PDFParseError(f"PDF 解析失败: {e}") from e

    return blocks
