#!/usr/bin/env python3
"""扫码登录微信 iLink Bot，凭证保存到 ~/.ilink_push/credentials.json。

用法:
    python login.py

首次使用需要手机微信扫描终端显示的二维码链接。
登录成功后凭证持久化，后续 push.py 无需重复登录。
"""

from __future__ import annotations

import asyncio
import sys

# 允许从项目根目录或任意位置运行
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ilink.auth import login_with_qr
from ilink.storage import save_credentials, clear_credentials


async def main() -> None:
    print("=" * 60)
    print("  微信 iLink Bot 扫码登录")
    print("=" * 60)
    print()

    def on_qr(url: str) -> None:
        print("📱 请在浏览器中打开以下链接，用微信扫描二维码：")
        print()
        print(f"   {url}")
        print()
        print("（如果链接太长，复制完整 URL 到浏览器打开即可）")
        print()

    try:
        creds = await login_with_qr(on_qr_url=on_qr, timeout=480)
    except RuntimeError as e:
        print(f"\n❌ 登录失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消登录")
        sys.exit(0)

    # 保存凭证
    path = save_credentials(
        token=creds["token"],
        account_id=creds["account_id"],
        base_url=creds["base_url"],
        user_id=creds["user_id"],
    )

    print()
    print("=" * 60)
    print("  ✅ 登录成功！")
    print(f"  凭证已保存至: {path}")
    print(f"  Account ID: {creds['account_id']}")
    print(f"  User ID:    {creds['user_id']}")
    print("=" * 60)
    print()
    print("现在可以使用了:")
    print('  python push.py "你好，这是测试消息"')
    print('  python push.py --file report.md')


if __name__ == "__main__":
    asyncio.run(main())
