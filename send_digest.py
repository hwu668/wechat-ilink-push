#!/usr/bin/env python3
"""财经日报推送脚本 —— 生成日报并通过微信发送。

依赖: ../advanced_investment_strategy 项目（同目录下）

用法:
    python send_digest.py              # 生成并推送文本摘要
    python send_digest.py --save        # 先保存 md 文件，再推送文件
    python send_digest.py --push-only   # 只推送，不重新生成（使用已有 md）
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 确保能找到 ilink 和 advanced_investment_strategy
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent / "advanced_investment_strategy"))

from ilink import get_client
from create_gist import create_gist


def _build_summary(md_path: str) -> str:
    """从日报 Markdown 中提取精简摘要。"""
    try:
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return ""

    lines = content.split("\n")
    summary_parts = []

    # 提取标题
    for line in lines:
        if line.startswith("# ") and "每日" in line:
            summary_parts.append(line.lstrip("# ").strip())

    # 提取市场主线
    in_narrative = False
    for line in lines:
        if "今日市场主线" in line:
            in_narrative = True
            continue
        if in_narrative:
            if line.startswith("## ") or line.startswith("---"):
                in_narrative = False
                continue
            stripped = line.strip()
            if stripped and not stripped.startswith(">"):
                summary_parts.append(stripped)
                break  # 只取第一段

    # 提取异动警报
    in_alerts = False
    alert_count = 0
    for line in lines:
        if "异动警报" in line:
            in_alerts = True
            continue
        if in_alerts:
            if line.startswith("## ") or line.startswith("---"):
                in_alerts = False
                continue
            stripped = line.strip()
            if stripped.startswith("- **") and alert_count < 5:
                # 精简: 去掉 markdown 标记
                clean = stripped.replace("**", "").replace("- ", "• ")[:120]
                summary_parts.append(clean)
                alert_count += 1

    return "\n".join(summary_parts) if summary_parts else ""


async def main() -> None:
    parser = argparse.ArgumentParser(description="财经日报推送到微信")
    parser.add_argument("--save", action="store_true", help="先生成 md 文件再推送")
    parser.add_argument("--push-only", action="store_true", help="仅推送已有文件")
    parser.add_argument(
        "--date", default=None,
        help="指定日期 (默认今天), 格式 YYYY-MM-DD",
    )
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    digest_dir = SCRIPT_DIR.parent / "advanced_investment_strategy"
    md_path = digest_dir / f"digest_{date_str}.md"

    # ── 生成日报 ──
    if not args.push_only:
        print(f"⏳ 正在生成财经日报 ({date_str})...")
        import subprocess
        result = subprocess.run(
            [sys.executable, "main.py", "news", "--save"],
            cwd=str(digest_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"❌ 日报生成失败:\n{result.stderr}")
            sys.exit(1)
        print("✅ 日报生成完成")

    # ── 读取日报 ──
    if not md_path.exists():
        print(f"❌ 日报文件不存在: {md_path}")
        print("   请先运行: cd advanced_investment_strategy && python main.py news --save")
        sys.exit(1)

    # ── 推送 ──
    try:
        client, user_id = get_client()
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    try:
        # 1. 上传完整报告到 secret gist
        today = datetime.now().strftime("%Y-%m-%d")
        gist_url = ""
        try:
            print("📤 上传完整报告到 secret gist...")
            gist_url = create_gist(str(md_path), description=f"每日金融资讯 {today}")
            print(f"   {gist_url}")
        except Exception as e:
            print(f"⚠️  gist 上传跳过: {e}")

        # 2. 发送精简摘要
        summary = _build_summary(str(md_path))

        if summary:
            header = f"📊 每日金融资讯 — {today}\n\n{summary}"
        else:
            header = f"📊 每日金融资讯 — {today}"

        # 3. 附加 gist 链接
        if gist_url:
            header += f"\n\n📄 完整报告: {gist_url}"

        print(f"📤 推送文本摘要 ({len(header)} 字符)...")
        await client.send_message(text=header, to_user_id=user_id)

        print("✅ 推送完成！请查看微信。")

    except Exception as e:
        print(f"❌ 推送失败: {e}")
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
