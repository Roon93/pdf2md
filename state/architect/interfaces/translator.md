# translator 模块接口

## 职责

调用内网 LLM API，对 Markdown 文本按段落翻译，生成双语对照版本。

## 函数签名

```python
def translate_markdown(
    markdown_text: str,
    api_url: str,
    api_key: str = "",
    model: str = "",
) -> str:
    """
    对 Markdown 文本按段落翻译，返回双语对照版本。

    Args:
        markdown_text: 原始 Markdown 文本
        api_url: LLM API 基础地址，如 http://10.0.0.1:8080
        api_key: API 认证密钥，可为空
        model: 模型名称，可为空（由服务端决定）

    Returns:
        双语对照 Markdown 字符串（原文段落 + 译文段落交替）
    """


def translate_paragraph(
    text: str,
    api_url: str,
    api_key: str = "",
    model: str = "",
) -> str:
    """
    翻译单个段落，返回译文字符串。
    失败时返回空字符串（调用方决定是否保留原文）。
    """
```

## LLM API 调用规范

- 端点：`POST {api_url}/v1/chat/completions`
- 认证：`Authorization: Bearer {api_key}`（api_key 为空时不发送此头）
- 请求体：
```json
{
  "model": "{model}",
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业翻译。请将用户提供的文本翻译为中文。只返回译文，不要解释，不要添加任何额外内容。"
    },
    {
      "role": "user",
      "content": "{paragraph_text}"
    }
  ],
  "temperature": 0.3
}
```

## 双语对照排版规则

对于每个段落（非标题、非代码块、非表格）：
```
原文段落

译文段落

```

标题、代码块、表格、图片不翻译，直接保留。

## 依赖

- Python 标准库：`urllib.request`, `urllib.error`, `json`, `sys`
