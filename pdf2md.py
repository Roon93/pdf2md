import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse

from src.pdf_parser import parse_pdf, PDFParseError
from src.md_converter import convert_to_markdown
from src.translator import translate_markdown
from src.utils import log_warn, log_error


def main():
    parser = argparse.ArgumentParser(
        description="将 PDF 文件转换为 Markdown 格式"
    )
    parser.add_argument("input_pdf", help="输入 PDF 文件路径")
    parser.add_argument("-o", "--output", dest="output", default=None, help="输出 .md 文件路径（默认：同输入文件名改 .md 扩展名）")
    parser.add_argument("--translate", action="store_true", help="启用翻译")
    parser.add_argument("--api-url", dest="api_url", default=None, help="LLM API 地址（启用翻译时必填）")
    parser.add_argument("--api-key", dest="api_key", default="", help="API 密钥")
    parser.add_argument("--model", dest="model", default="", help="模型名称")

    args = parser.parse_args()

    # 3. 若 --translate 但未提供 --api-url（提前检查，无需文件存在）
    if args.translate and not args.api_url:
        log_error("启用翻译时必须提供 --api-url 参数")
        sys.exit(1)

    # 1. 检查 input_pdf 存在
    if not os.path.exists(args.input_pdf):
        log_error(f"输入文件不存在: {args.input_pdf}")
        sys.exit(1)

    # 2. 确定 output_path
    if args.output:
        output_path = args.output
    else:
        base, _ = os.path.splitext(args.input_pdf)
        output_path = base + ".md"

    # 4. image_output_dir
    image_output_dir = os.path.dirname(os.path.abspath(output_path))

    try:
        # 5. 解析 PDF
        blocks = parse_pdf(args.input_pdf, image_output_dir)
    except PDFParseError as e:
        log_error(f"PDF 解析失败: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        log_error(f"文件未找到: {e}")
        sys.exit(1)

    # 6. 转换为 Markdown
    md_text = convert_to_markdown(blocks)

    # 7. 翻译（可选）
    if args.translate:
        md_text = translate_markdown(md_text, args.api_url, args.api_key, args.model)

    # 8. 写入输出文件
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_text)
    except Exception as e:
        log_error(f"写入文件失败: {e}")
        sys.exit(1)

    # 9. 完成提示
    print(f"转换完成: {output_path}")


if __name__ == "__main__":
    main()
