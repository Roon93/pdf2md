#!/bin/bash
# 在有网络的机器上执行，将 poppler + ghostscript 打包到 tools/ 目录
# 执行后需将整个 tools/ 目录复制到内网机器
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$SCRIPT_DIR"

# 下载 RPM
TMPDIR=$(mktemp -d)
yumdownloader --destdir="$TMPDIR" --resolve poppler poppler-utils ghostscript ghostscript-tools-fonts ghostscript-tools-printing poppler-data

# 提取
mkdir -p "$TMPDIR/extracted"
cd "$TMPDIR/extracted"
for rpm in "$TMPDIR"/*.rpm; do
  rpm2cpio "$rpm" | cpio -idv 2>/dev/null
done

# 复制到 tools/
rm -rf "$TOOLS_DIR/usr" "$TOOLS_DIR/lib64" "$TOOLS_DIR/share"
cp -r "$TMPDIR/extracted/usr" "$TOOLS_DIR/"
cp -r "$TMPDIR/extracted/usr/lib64" "$TOOLS_DIR/" 2>/dev/null || true

# 清理
rm -rf "$TMPDIR"
echo "Done. tools/ 目录已就绪。"
echo "请将 tools/ 目录复制到内网机器的 pdf2md/ 目录下。"
