# pdf2md 项目需求文档

## 项目概述

将单个纯文本 PDF 文件转换为 Markdown 格式，可选对内容进行中文翻译。工具以命令行方式运行，适用于内网离线环境。

---

## 环境约束

- Python 版本：3.8
- 操作系统：Ubuntu Server
- 网络环境：内网隔离，无法访问外网
- 不可通过 pip 或系统包管理器安装额外依赖
- 允许使用 subprocess 调用系统命令
- 内网提供 LLM API，接口兼容 OpenAI 格式（/v1/chat/completions）

---

## 功能需求

### F01 - PDF 转 Markdown

- 输入：单个纯文本 PDF 文件
- 输出：Markdown 文件
- 默认输出路径：与输入文件同目录，同名，扩展名改为 `.md`
- 支持通过 `-o` 参数自定义输出路径

### F02 - 格式保留

转换时需识别并保留以下格式：

| 原始格式 | Markdown 输出 |
|----------|---------------|
| 标题（H1 / H2 / H3） | `#` / `##` / `###` |
| 有序列表 | `1. 2. 3.` |
| 无序列表 | `- ` |
| 表格 | GFM 表格语法 |
| 粗体 | `**text**` |
| 斜体 | `*text*` |

### F03 - 图片提取

- 从 PDF 中提取嵌入图片，保存为独立文件（如 `image_001.png`）
- 在 Markdown 中以 `![](path/to/image_001.png)` 形式引用
- 图片保存路径与输出 Markdown 文件同目录

### F04 - 可选翻译功能

通过 `--translate` 参数启用，行为如下：

- 自动检测源语言
- 目标语言固定为中文
- 翻译粒度：按段落逐段调用 LLM API
- 排版方式：原文段落紧跟译文段落（双语对照）
- 翻译接口：内网 LLM API，OpenAI 兼容格式

---

## 技术约束

### PDF 解析

- 使用 pdfminer.six 进行 PDF 文本提取
- pdfminer.six 源码以 vendor 方式打包进项目目录，不依赖 pip 安装
- 项目结构示例：`vendor/pdfminer/` 存放源码，运行时通过 `sys.path` 注入

### LLM 调用

- 使用 Python 标准库 `urllib` 或 `http.client` 发起 HTTP 请求
- 不引入 `requests` 或其他第三方 HTTP 库
- 请求格式：POST `/v1/chat/completions`，JSON body，Bearer Token 认证

---

## CLI 接口设计

```
python pdf2md.py <input.pdf> [-o output.md] [--translate] [--api-url URL] [--api-key KEY] [--model MODEL]
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input.pdf` | 位置参数 | 是 | 输入 PDF 文件路径 |
| `-o output.md` | 可选 | 否 | 输出 Markdown 文件路径，默认同输入文件名改扩展名 |
| `--translate` | 开关 | 否 | 启用翻译功能 |
| `--api-url URL` | 可选 | 翻译时必填 | LLM API 地址，如 `http://10.0.0.1:8080` |
| `--api-key KEY` | 可选 | 否 | API 认证密钥，默认为空 |
| `--model MODEL` | 可选 | 否 | 使用的模型名称，默认由 API 服务端决定 |

### 使用示例

```bash
# 基本转换
python pdf2md.py report.pdf

# 指定输出路径
python pdf2md.py report.pdf -o /tmp/report.md

# 启用翻译
python pdf2md.py report.pdf --translate --api-url http://10.0.0.1:8080 --api-key sk-xxx --model qwen2
```

---

## 假设与边界

- 仅处理纯文本 PDF，不支持扫描件（图像型 PDF）
- 单文件处理，不支持批量转换
- 标题层级识别基于字体大小或样式推断，可能存在误判
- 翻译质量依赖内网 LLM 能力，工具本身不做质量保证
