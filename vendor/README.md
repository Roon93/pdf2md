# vendor 目录说明

本目录用于存放离线依赖包，主要是 `pdfminer.six` 的源码，供内网（无网络）环境使用。

## 目录结构

```
vendor/
├── README.md            # 本文件
├── fetch_pdfminer.sh    # 在有网络的机器上执行，下载 pdfminer 源码
└── pdfminer/            # 执行脚本后生成，pdfminer 源码包
```

## 使用流程

### 第一步：在有网络的机器上打包

```bash
bash vendor/fetch_pdfminer.sh
```

执行后会在 `vendor/pdfminer/` 下生成 pdfminer 的源码目录。

### 第二步：将整个 vendor/ 目录复制到内网机器

```bash
# 示例：通过 scp 复制
scp -r vendor/ user@内网机器:/path/to/pdf2md/
```

### 第三步：运行时注入路径

在主程序或入口脚本中，将 `vendor/` 目录加入 Python 模块搜索路径：

```python
import sys
import os

# 将 vendor 目录加入模块搜索路径
vendor_dir = os.path.join(os.path.dirname(__file__), "vendor")
sys.path.insert(0, vendor_dir)

# 之后即可正常导入 pdfminer
from pdfminer.high_level import extract_text
```

或者通过环境变量设置：

```bash
PYTHONPATH=vendor:$PYTHONPATH python3 pdf2md.py input.pdf
```
