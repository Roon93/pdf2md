"""
工具函数模块：提供日志输出等通用工具。
"""
import sys


def log_warn(msg: str) -> None:
    """向 stderr 打印警告信息。"""
    print(f"[WARN] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    """向 stderr 打印错误信息。"""
    print(f"[ERROR] {msg}", file=sys.stderr)
