#!/bin/bash
# 在有网络的机器上执行，将 pdfminer 源码下载到 vendor/ 目录
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
pip download pdfminer.six==20221105 --no-deps -d /tmp/pdfminer_pkg
cd /tmp/pdfminer_pkg
unzip -o pdfminer.six-*.whl -d /tmp/pdfminer_extracted
cp -r /tmp/pdfminer_extracted/pdfminer "$SCRIPT_DIR/"
echo "Done. vendor/pdfminer/ 已就绪。"
