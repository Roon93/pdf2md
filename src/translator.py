"""
翻译模块：调用 OpenAI 兼容 API 将文本翻译为中文。
带 429 重试（指数退避）和 RPM 限流保护。
"""
import json
import time
import urllib.request
import urllib.error

from .utils import log_warn

_SYSTEM_PROMPT = (
    "你是一个专业翻译。请将用户提供的文本翻译为中文。"
    "只返回译文，不要解释，不要添加任何额外内容。"
)

# API 调用参数
DEFAULT_MAX_RETRIES = 5       # 最多重试 5 次（429 时）
DEFAULT_BASE_DELAY = 1.0     # 首次重试延迟 1 秒
DEFAULT_MAX_DELAY = 120.0    # 最长延迟 120 秒
DEFAULT_RPM = 60             # 默认 RPM 限流值（可配置）


class RateLimiter:
    """简单滑动窗口 RPM 限流器。"""

    def __init__(self, rpm: float):
        self.rpm = rpm
        self.interval = 60.0 / rpm if rpm > 0 else 0
        self.last_request_time = 0.0

    def wait(self):
        """等待足够时间使请求频率不超过 RPM。"""
        if self.interval <= 0:
            return
        elapsed = time.time() - self.last_request_time
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_request_time = time.time()


def translate_paragraph(
    text: str,
    api_url: str,
    api_key: str = "",
    model: str = "",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
) -> str:
    """调用 API 翻译单段文本，429 时指数退避重试，失败时返回空字符串。"""
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

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                if attempt < max_retries:
                    # 429 时从 Retry-After 头读取等待时间，否则指数退避
                    retry_after = e.headers.get("Retry-After")
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                    log_warn(f"API 限流 (429)，{delay:.1f}s 后重试（第 {attempt + 1}/{max_retries} 次）")
                    time.sleep(delay)
                    continue
            # 非 429 或已达最大重试次数，记录错误并返回空
            log_warn(f"translate_paragraph 失败 (HTTP {e.code}): {e}")
            return ""
        except Exception as e:
            last_error = e
            log_warn(f"translate_paragraph 失败: {e}")
            return ""

    log_warn(f"translate_paragraph 超过最大重试次数: {last_error}")
    return ""


def translate_markdown(
    markdown_text: str,
    api_url: str,
    api_key: str = "",
    model: str = "",
    rpm: float = DEFAULT_RPM,
) -> str:
    """翻译 Markdown 文本，保留标题/表格/图片/代码块，普通段落追加译文。"""
    limiter = RateLimiter(rpm)

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

        # 普通段落：限流等待 + 翻译后追加
        limiter.wait()
        translation = translate_paragraph(stripped, api_url, api_key, model)
        if translation:
            result.append(para + "\n\n" + translation)
        else:
            result.append(para)

    return "\n\n".join(result)
