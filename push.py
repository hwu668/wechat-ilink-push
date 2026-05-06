#!/usr/bin/env python3
"""向自己推送消息或文件。

用法:
    # 推送文本
    python push.py "今日财经日报已生成，请查看。"

    # 推送文件
    python push.py --file digest_2026-05-06.md

    # 推送文件 + 文字说明
    python push.py --file digest_2026-05-06.md -m "📊 每日金融资讯"

    # 从 stdin 推送（适合管道）
    echo "Hello" | python push.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ilink import get_client


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="微信 iLink Bot 消息推送",
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="要发送的文本消息（留空则从 stdin 读取）",
    )
    parser.add_argument(
        "--file", "-f",
        help="要发送的文件路径",
    )
    parser.add_argument(
        "--message", "-m",
        default="",
        help="伴随文件的文字说明",
    )
    args = parser.parse_args()

    # 获取文本内容
    text = args.text or ""
    if not text and not args.file and not sys.stdin.isatty():
        text = sys.stdin.read().strip()

    if not text and not args.file:
        parser.print_help()
        print("\n❌ 请提供消息文本或文件路径")
        sys.exit(1)

    # 获取客户端
    try:
        client = get_client()
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    try:
        if args.file:
            # 发送文件
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"❌ 文件不存在: {args.file}")
                sys.exit(1)

            print(f"📤 正在发送文件: {file_path.name} ({file_path.stat().st_size} bytes)")
            caption = args.message or args.text or ""
            await client.send_file(
                file_path=str(file_path),
                caption=caption,
            )
            print(f"✅ 文件已发送: {file_path.name}")

        else:
            # 发送纯文本
            print(f"📤 正在发送消息 ({len(text)} 字符)...")
            resp = await client.send_message(text=text)
            ret = resp.get("ret", -1)
            if ret and ret != 0:
                print(f"⚠️  服务器返回错误: {resp}")
            else:
                print("✅ 消息已发送")

    except Exception as e:
        print(f"❌ 发送失败: {e}")
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
