"""
翻译模块：调用 OpenAI 兼容 API 将文本翻译为中文。
"""
import json
import urllib.request

from src.utils import log_warn

_SYSTEM_PROMPT = (
    "你是一个专业翻译。请将用户提供的文本翻译为中文。"
    "只返回译文，不要解释，不要添加任何额外内容。"
)


def translate_paragraph(text: str, api_url: str, api_key: str = "", model: str = "") -> str:
    """调用 API 翻译单段文本，失败时返回空字符串。"""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{api_url}/v1/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log_warn(f"translate_paragraph 失败: {e}")
        return ""


def translate_markdown(
    markdown_text: str, api_url: str, api_key: str = "", model: str = ""
) -> str:
    """翻译 Markdown 文本，保留标题/表格/图片/代码块，普通段落追加译文。"""
    paragraphs = markdown_text.split("\n\n")
    result = []
    in_code_block = False

    for para in paragraphs:
        stripped = para.strip()

        # 空段落直接保留
        if not stripped:
            result.append(para)
            continue

        # 跟踪代码块状态
        if stripped.startswith("```") or stripped.endswith("```"):
            in_code_block = not in_code_block
            result.append(para)
            continue

        if in_code_block:
            result.append(para)
            continue

        # 不翻译的段落类型
        if (
            stripped.startswith("#")
            or stripped.startswith("|")
            or stripped.startswith("![")
        ):
            result.append(para)
            continue

        # 普通段落：翻译后追加
        translation = translate_paragraph(stripped, api_url, api_key, model)
        if translation:
            result.append(para + "\n\n" + translation)
        else:
            result.append(para)

    return "\n\n".join(result)
