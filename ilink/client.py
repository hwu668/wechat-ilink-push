"""iLink Bot HTTP 客户端 —— 仅依赖 httpx。

实现：
  - send_message()   发送文本消息给自己
  - send_file()      上传并发送文件
  - get_upload_url() 获取 CDN 上传地址
"""

from __future__ import annotations

import base64
import os
import struct
import uuid
from pathlib import Path
from typing import Optional

import httpx

# ─── 协议常量 ────────────────────────────────────────────

BASE_URL = "https://ilinkai.weixin.qq.com"
APP_ID = "wx_bot_python"
CLIENT_VERSION = "1.0.0"

# 消息类型枚举
MSG_TYPE_TEXT = 1
MSG_TYPE_IMAGE = 2
MSG_TYPE_FILE = 4
MSG_TYPE_VIDEO = 5

MSG_STATE_FINISH = 2
MSG_TYPE_BOT = 2


# ─── 工具函数 ────────────────────────────────────────────

def _random_uin() -> str:
    """生成 X-WECHAT-UIN 头：随机 uint32 → 十进制字符串 → base64。"""
    raw = os.urandom(4)
    uint32 = struct.unpack(">I", raw)[0]
    return base64.b64encode(str(uint32).encode()).decode()


def _client_id() -> str:
    return f"ilink-push-{uuid.uuid4().hex[:12]}"


def _build_client_version(v: str) -> str:
    """将 x.y.z 编码为 uint32 字符串: 0x00MMNNPP。"""
    parts = v.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return str(((major & 0xFF) << 16) | ((minor & 0xFF) << 8) | (patch & 0xFF))


# ─── HTTP 客户端 ─────────────────────────────────────────

class ILinkClient:
    """iLink Bot API 的轻量异步 HTTP 客户端。"""

    def __init__(self, token: str, base_url: str = BASE_URL):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._http: Optional[httpx.AsyncClient] = None

    async def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._http

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "AuthorizationType": "ilink_bot_token",
            "X-WECHAT-UIN": _random_uin(),
            "iLink-App-Id": APP_ID,
            "iLink-App-ClientVersion": _build_client_version(CLIENT_VERSION),
        }

    # ─── 核心 API ────────────────────────────────────────

    async def send_message(
        self,
        text: str,
        to_user_id: str = "",
        context_token: str = "",
    ) -> dict:
        """发送文本消息。

        Args:
            text: 消息内容（纯文本，不支持 Markdown 渲染）
            to_user_id: 目标用户 ID，空字符串 = 发给自己
            context_token: 会话上下文令牌，首次可空
        """
        body = {
            "msg": {
                "from_user_id": "",
                "to_user_id": to_user_id,
                "client_id": _client_id(),
                "message_type": MSG_TYPE_BOT,
                "message_state": MSG_STATE_FINISH,
                "item_list": [
                    {
                        "type": MSG_TYPE_TEXT,
                        "text_item": {"text": text},
                    }
                ],
                "context_token": context_token,
            }
        }

        http = await self._ensure_http()
        resp = await http.post(
            f"{self.base_url}/ilink/bot/sendmessage",
            json=body,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_upload_url(
        self,
        file_name: str,
        file_size: int,
        file_md5: str = "",
        media_type: int = MSG_TYPE_FILE,
        to_user_id: str = "",
    ) -> dict:
        """获取 CDN 预签名上传 URL。

        Args:
            file_name: 文件名
            file_size: 文件大小（字节）
            file_md5: 文件 MD5（可选）
            media_type: 媒体类型 (2=图片, 3=视频, 4=文件)
            to_user_id: 接收方用户 ID
        """
        body = {
            "file_name": file_name,
            "file_size": file_size,
            "file_md5": file_md5,
            "media_type": media_type,
            "ilink_user_id": to_user_id,
            "base_info": {"channel_version": CLIENT_VERSION},
        }

        http = await self._ensure_http()
        resp = await http.post(
            f"{self.base_url}/ilink/bot/getuploadurl",
            json=body,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def send_file(
        self,
        file_path: str,
        caption: str = "",
        to_user_id: str = "",
        context_token: str = "",
    ) -> None:
        """上传并发送文件。

        Args:
            file_path: 本地文件路径
            caption: 伴随的文本说明（可选）
            to_user_id: 目标用户 ID
            context_token: 会话上下文令牌
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_size = path.stat().st_size
        file_name = path.name

        # 1. 获取上传 URL
        upload_info = await self.get_upload_url(
            file_name=file_name,
            file_size=file_size,
            to_user_id=to_user_id,
        )

        # 2. 上传文件到 CDN
        upload_url = upload_info.get("upload_url", "")
        if not upload_url:
            raise RuntimeError(f"获取上传地址失败: {upload_info}")

        http = await self._ensure_http()
        with open(file_path, "rb") as f:
            upload_resp = await http.put(
                upload_url,
                content=f.read(),
                headers={"Content-Type": "application/octet-stream"},
            )
            upload_resp.raise_for_status()

        # 3. 构建文件消息并发送
        cdn_info = {
            "file_name": file_name,
            "file_size": file_size,
            "file_md5": upload_info.get("file_md5", ""),
            "cdn_url": upload_info.get("cdn_url", ""),
            "aes_key": upload_info.get("aes_key", ""),
        }

        items = []
        if caption:
            items.append({"type": MSG_TYPE_TEXT, "text_item": {"text": caption}})
        items.append({"type": MSG_TYPE_FILE, "file_item": cdn_info})

        # 逐条发送
        for item in items:
            body = {
                "msg": {
                    "from_user_id": "",
                    "to_user_id": to_user_id,
                    "client_id": _client_id(),
                    "message_type": MSG_TYPE_BOT,
                    "message_state": MSG_STATE_FINISH,
                    "item_list": [item],
                    "context_token": context_token,
                }
            }
            resp = await http.post(
                f"{self.base_url}/ilink/bot/sendmessage",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
