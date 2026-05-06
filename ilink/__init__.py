"""ilink_push —— 零第三方依赖的微信 iLink Bot 推送模块。

仅依赖 httpx（HTTP 客户端）。

使用示例:

    # 扫码登录（一次性）
    python login.py

    # 推送消息
    python push.py "今日财经日报已生成"

    # 推送文件
    python push.py --file digest_2026-05-06.md

    # 从代码调用
    from ilink import get_client, send_text
    client = get_client()   # 自动加载 ~/.ilink_push/credentials.json
    import asyncio
    asyncio.run(client.send_message("Hello from Python!"))
"""

from .client import ILinkClient
from .auth import login_with_qr
from .storage import (
    save_credentials,
    load_credentials,
    clear_credentials,
    has_credentials,
)

__all__ = [
    "ILinkClient",
    "login_with_qr",
    "save_credentials",
    "load_credentials",
    "clear_credentials",
    "has_credentials",
    "get_client",
]

__version__ = "1.0.0"


def get_client() -> tuple[ILinkClient, str]:
    """快速获取已认证的客户端和 user_id。

    Returns:
        (client, user_id) — user_id 用于 to_user_id 参数
    """
    creds = load_credentials()
    token = creds.get("token", "")
    base_url = creds.get("base_url", "https://ilinkai.weixin.qq.com")
    user_id = creds.get("user_id", "")
    if not token:
        raise RuntimeError(
            "未找到登录凭证。请先运行: python login.py"
        )
    return ILinkClient(token=token, base_url=base_url), user_id
