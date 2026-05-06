"""iLink Bot HTTP 客户端 —— 仅依赖 httpx。

基于微信官方 ClawBot 插件的 TypeScript 参考实现。
协议细节对齐 @tencent-weixin/openclaw-weixin。

实现：
  - send_message()   发送文本消息
  - send_file()      上传并发送文件（暂未实现 CDN 上传链路）
"""

from __future__ import annotations

import base64
import os
import struct
import uuid
from pathlib import Path
from typing import Optional

import httpx

# ─── 协议常量（对齐 TypeScript 参考实现）─────────────────

BASE_URL = "https://ilinkai.weixin.qq.com"

MSG_TYPE_TEXT = 1
MSG_TYPE_FILE = 4
MSG_STATE_FINISH = 2
MSG_TYPE_BOT = 2


# ─── 工具函数 ────────────────────────────────────────────

def _random_uin() -> str:
    """X-WECHAT-UIN: 随机 uint32 → 十进制字符串 → base64。"""
    raw = os.urandom(4)
    uint32 = struct.unpack(">I", raw)[0]
    return base64.b64encode(str(uint32).encode()).decode()


def _client_id() -> str:
    """生成唯一 client_id。"""
    return f"bot-{uuid.uuid4().hex[:12]}"


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
        """标准请求头（对齐 TypeScript buildHeaders）。"""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "X-WECHAT-UIN": _random_uin(),
            "iLink-App-Id": "wx_bot_python",
            "iLink-App-ClientVersion": "258",  # 0x00_01_02 = 0x0102 = 258
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ─── 核心 API ────────────────────────────────────────

    async def send_message(
        self,
        text: str,
        to_user_id: str,
        context_token: Optional[str] = None,
    ) -> dict:
        """发送文本消息（对齐 TypeScript sendTextMessage）。

        Args:
            text: 消息内容（纯文本）
            to_user_id: 目标用户 ID（必填）
            context_token: 会话上下文令牌（留空则自动从磁盘加载）
        """
        # 未显式传入时自动加载持久化的 context_token
        if not context_token:
            from .storage import load_context_token
            context_token = load_context_token()

        # 构建 msg（from_user_id 留空由服务端填充，None 字段序列化时自动排除）
        msg: dict = {
            "from_user_id": "",
            "to_user_id": to_user_id,
            "client_id": _client_id(),
            "message_type": MSG_TYPE_BOT,
            "message_state": MSG_STATE_FINISH,
            "item_list": [
                {"type": MSG_TYPE_TEXT, "text_item": {"text": text}}
            ],
        }
        if context_token:
            msg["context_token"] = context_token

        body = {
            "msg": msg,
            "base_info": {"channel_version": "2.0.0"},
        }

        http = await self._ensure_http()
        resp = await http.post(
            f"{self.base_url}/ilink/bot/sendmessage",
            json=body,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_updates(self, buf: str = "", timeout_ms: int = 35000) -> dict:
        """长轮询获取新消息（对齐 TypeScript getUpdates）。

        Args:
            buf: 增量同步游标
            timeout_ms: 服务端长轮询超时（毫秒）
        """
        body = {
            "get_updates_buf": buf,
            "base_info": {"channel_version": "2.0.0"},
        }
        http = await self._ensure_http()
        client_timeout = (timeout_ms / 1000.0) + 5.0
        try:
            resp = await http.post(
                f"{self.base_url}/ilink/bot/getupdates",
                json=body,
                headers=self._headers(),
                timeout=client_timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.ReadTimeout:
            return {"ret": 0, "msgs": [], "get_updates_buf": buf}
