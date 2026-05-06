"""扫码登录流程 —— 通过终端打印二维码 URL，用户用微信扫码确认。

用法:
    result = asyncio.run(login_with_qr())
    print(f"Token: {result['token']}")
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

import httpx

# ─── 常量 ────────────────────────────────────────────────

_AUTH_BASE = "https://ilinkai.weixin.qq.com"
_BOT_TYPE = "3"
_QR_TIMEOUT = 10.0        # 获取二维码超时
_POLL_TIMEOUT = 35.0       # 轮询超时
_MAX_REFRESH = 3           # 二维码过期最多刷新次数
_LOGIN_TIMEOUT = 480       # 总超时（秒）


# ─── QR 状态 ─────────────────────────────────────────────

class QRStatus:
    WAIT = "wait"
    SCANNED = "scaned"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    REDIRECT = "scaned_but_redirect"


# ─── 登录流程 ────────────────────────────────────────────

async def login_with_qr(
    on_qr_url: Optional[Callable[[str], None]] = None,
    timeout: int = _LOGIN_TIMEOUT,
) -> dict:
    """执行扫码登录，返回凭证字典。

    Returns:
        {
            "token": str,          # bot_token
            "account_id": str,     # ilink_bot_id
            "base_url": str,       # API base URL
            "user_id": str,        # ilink_user_id
        }

    Raises:
        RuntimeError: 登录超时或失败
    """
    async with httpx.AsyncClient() as http:
        # 1. 获取二维码
        qrcode_key, qrcode_url = await _fetch_qrcode(http)

        if on_qr_url:
            on_qr_url(qrcode_url)

        # 2. 轮询状态
        poll_base = _AUTH_BASE
        refresh_count = 0
        deadline = asyncio.get_event_loop().time() + timeout
        scanned = False

        while asyncio.get_event_loop().time() < deadline:
            try:
                data = await _poll_status(http, poll_base, qrcode_key)
            except (httpx.ReadTimeout, httpx.ConnectTimeout):
                await asyncio.sleep(1)
                continue

            status = data.get("status", QRStatus.WAIT)

            if status == QRStatus.WAIT:
                pass

            elif status == QRStatus.SCANNED:
                if not scanned:
                    print("\n✅ 已扫码，请在手机上确认登录...")
                    scanned = True

            elif status == QRStatus.CONFIRMED:
                token = data.get("bot_token", "")
                account_id = data.get("ilink_bot_id", "")
                result_base_url = data.get("baseurl") or _AUTH_BASE
                user_id = data.get("ilink_user_id", "")

                if not account_id:
                    raise RuntimeError("登录确认但服务器未返回 ilink_bot_id")

                return {
                    "token": token,
                    "account_id": account_id,
                    "base_url": result_base_url,
                    "user_id": user_id,
                }

            elif status == QRStatus.EXPIRED:
                refresh_count += 1
                if refresh_count >= _MAX_REFRESH:
                    raise RuntimeError("二维码过期次数过多，请重试")
                print(f"⚠️  二维码已过期，正在刷新 ({refresh_count}/{_MAX_REFRESH})...")
                qrcode_key, qrcode_url = await _fetch_qrcode(http)
                scanned = False
                if on_qr_url:
                    on_qr_url(qrcode_url)

            elif status == QRStatus.REDIRECT:
                redirect_host = data.get("redirect_host", "")
                if redirect_host:
                    poll_base = f"https://{redirect_host}"
                    print(f"🔄 重定向至: {poll_base}")

            await asyncio.sleep(1.5)

        raise RuntimeError(f"登录超时（{timeout}秒），请重试")


async def _fetch_qrcode(http: httpx.AsyncClient) -> tuple[str, str]:
    """获取二维码，返回 (qrcode_key, qrcode_image_url)。"""
    resp = await http.get(
        f"{_AUTH_BASE}/ilink/bot/get_bot_qrcode?bot_type={_BOT_TYPE}",
        timeout=_QR_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    qrcode_key = data.get("qrcode", "")
    qrcode_url = data.get("qrcode_img_content", "")
    if not qrcode_key:
        raise RuntimeError("服务器未返回二维码 key")
    return qrcode_key, qrcode_url


async def _poll_status(
    http: httpx.AsyncClient,
    base_url: str,
    qrcode_key: str,
) -> dict:
    """轮询扫码状态。"""
    resp = await http.get(
        f"{base_url.rstrip('/')}/ilink/bot/get_qrcode_status?qrcode={qrcode_key}",
        timeout=_POLL_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
