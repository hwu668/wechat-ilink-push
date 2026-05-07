#!/usr/bin/env python3
"""将 Markdown 文件上传为 GitHub secret gist，返回可分享的 URL。

Secret gist 不会被搜索引擎收录，仅有知道链接的人能访问。

用法:
    python create_gist.py digest_2026-05-06.md                  # 独立使用
    python create_gist.py digest_2026-05-06.md -d "每日金融资讯"  # 带描述
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def create_gist(md_path: str | Path, description: str = "") -> str:
    """上传 Markdown 文件为 secret gist，返回 gist URL。

    Args:
        md_path: Markdown 文件路径
        description: gist 描述（可选）

    Returns:
        gist URL，形如 https://gist.github.com/hwu668/abc123def456

    Raises:
        FileNotFoundError: 文件不存在
        RuntimeError: gh CLI 执行失败
    """
    path = Path(md_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {md_path}")

    cmd = ["gh", "gist", "create", str(path)]
    if description:
        cmd.extend(["--desc", description])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"gist 创建失败: {result.stderr.strip() or '未知错误'}")

    # gh gist create 最后一行是 URL
    url = result.stdout.strip().split("\n")[-1]
    if not url.startswith("https://gist.github.com/"):
        raise RuntimeError(f"无法从输出中提取 gist URL: {result.stdout}")

    return url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="上传文件为 GitHub secret gist"
    )
    parser.add_argument("file", help="Markdown 文件路径")
    parser.add_argument("-d", "--desc", default="", help="gist 描述")
    args = parser.parse_args()

    try:
        url = create_gist(args.file, args.desc)
        print(url)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
