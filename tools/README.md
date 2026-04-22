# tools 目录说明

本目录用于存放 PDF 工具的二进制文件和依赖库，供内网（无网络）环境使用。

## 包含内容

```
tools/
├── usr/bin/              # 可执行文件
│   ├── pdftoppm          # PDF 转图片工具（poppler-utils）
│   ├── pdftocairo         # PDF 渲染工具（回退）
│   ├── gs                 # Ghostscript
│   └── ...                # 其他 poppler/ghostscript 工具
├── lib64/                 # 共享库
│   ├── libpoppler.so.130  # poppler 核心库
│   └── ...
└── README.md             # 本文件
```

## 打包步骤（在一台有网络的 OpenCloudOS 9 机器上执行）

```bash
# 1. 安装下载工具
yum install -y yum-utils

# 2. 下载 RPM 包（包含所有依赖）
mkdir -p /tmp/rpm-pkgs
yumdownloader --destdir=/tmp/rpm-pkgs --resolve poppler poppler-utils ghostscript ghostscript-tools-fonts ghostscript-tools-printing poppler-data

# 3. 创建打包目录
mkdir -p /tmp/rpm-all
cd /tmp/rpm-all
for rpm in /tmp/rpm-pkgs/*.rpm; do
  rpm2cpio "$rpm" | cpio -idv
done

# 4. 复制到项目
cp -r /tmp/rpm-all/usr /path/to/pdf2md/tools/
```

## 使用说明

`pdf_parser.py` 会自动使用 `tools/usr/bin/pdftoppm` 或 `tools/usr/bin/pdftocairo` 渲染矢量图（流程图、线条图）。
如工具目录不存在，矢量图将被跳过并打印警告。

gs (Ghostscript) 依赖 `lib64/` 中的共享库，直接复制到内网机器后可能需要设置 `LD_LIBRARY_PATH`：

```bash
export LD_LIBRARY_PATH=/path/to/pdf2md/tools/lib64:$LD_LIBRARY_PATH
python3 pdf2md.py input.pdf
```
