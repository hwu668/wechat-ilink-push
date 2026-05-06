#!/usr/bin/env python3
"""扫码登录微信 iLink Bot，凭证保存到 ~/.ilink_push/credentials.json。

用法:
    python login.py

首次使用需要手机微信扫描二维码图片。
二维码链接会自动在浏览器中打开（如无法自动打开，请手动复制终端打印的链接）。
"""

from __future__ import annotations

import asyncio
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ilink.auth import login_with_qr
from ilink.storage import save_credentials


async def main() -> None:
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  微信 iLink Bot 扫码登录".center(52) + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    qr_url_shown = False

    def on_qr(url: str) -> None:
        nonlocal qr_url_shown
        # 尝试自动打开浏览器
        try:
            webbrowser.open(url)
            print("🌐 已自动打开浏览器，如未弹出请手动复制下方链接。")
        except Exception:
            pass

        print()
        print("┌" + "─" * 58 + "┐")
        print("│ 📱 请用微信扫描二维码（在浏览器中打开该链接）：".ljust(56) + "│")
        print("│".ljust(56) + "│")
        print(f"│   {url}".ljust(56) + "│")
        print("│".ljust(56) + "│")
        print("│ （手机上确认登录后，此处自动完成）".ljust(50) + "│")
        print("└" + "─" * 58 + "┘")
        print()
        qr_url_shown = True

    try:
        creds = await login_with_qr(on_qr_url=on_qr, timeout=480)
    except RuntimeError as e:
        print(f"\n❌ 登录失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消")
        sys.exit(0)

    # 保存凭证
    path = save_credentials(
        token=creds["token"],
        account_id=creds["account_id"],
        base_url=creds["base_url"],
        user_id=creds["user_id"],
    )

    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ✅ 登录成功！".center(52) + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  凭证: {path}".ljust(56) + "║")
    print(f"║  Account: {creds['account_id']}".ljust(56) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("  试试看:")
    print('    python push.py "你好，测试消息 🎉"')
    print()


if __name__ == "__main__":
    asyncio.run(main())
