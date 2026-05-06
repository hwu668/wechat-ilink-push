#!/usr/bin/env python3
"""扫码登录微信 iLink Bot，凭证保存到 ~/.ilink_push/credentials.json。

用法:
    python login.py

二维码直接在终端中显示（ASCII 渲染），用微信扫描即可。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ilink.auth import login_with_qr
from ilink.storage import save_credentials


def _print_qr_terminal(url: str) -> None:
    """在终端中渲染二维码（ASCII）。"""
    try:
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        print()
        qr.print_ascii(invert=True)
        print()
    except ImportError:
        pass  # 回退到只打印 URL


async def main() -> None:
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  微信 iLink Bot 扫码登录".center(52) + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    def on_qr(url: str) -> None:
        # 终端 ASCII 二维码
        _print_qr_terminal(url)
        # 同时打印链接作为备用
        print(f"📎 备用链接（若二维码不清晰，在浏览器打开）：")
        print(f"   {url}")
        print()
        print("⏳ 等待扫码...（手机上确认后自动完成）")

    try:
        creds = await login_with_qr(on_qr_url=on_qr, timeout=480)
    except RuntimeError as e:
        print(f"\n❌ 登录失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消")
        sys.exit(0)

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
