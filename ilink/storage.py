"""Token 本地持久化 —— 零第三方依赖。

凭证保存在 ~/.ilink_push/credentials.json，权限 0o600。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

STATE_DIR = os.path.join(os.path.expanduser("~"), ".ilink_push")
CREDENTIALS_FILE = "credentials.json"
_PRIVATE_DIR_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    if os.name != "nt":
        os.chmod(path, _PRIVATE_DIR_MODE)


def save_credentials(
    token: str,
    account_id: str = "",
    base_url: str = "",
    user_id: str = "",
) -> str:
    """保存登录凭证，返回凭证文件路径。"""
    _ensure_dir(STATE_DIR)
    data = {
        "token": token,
        "account_id": account_id,
        "base_url": base_url or "https://ilinkai.weixin.qq.com",
        "user_id": user_id,
    }
    path = os.path.join(STATE_DIR, CREDENTIALS_FILE)

    # 原子写入：临时文件 + os.replace
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.name != "nt":
            os.chmod(tmp, _PRIVATE_FILE_MODE)
        os.replace(tmp, path)
        if os.name != "nt":
            os.chmod(path, _PRIVATE_FILE_MODE)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

    return path


def load_credentials() -> dict[str, str]:
    """读取持久化的凭证。"""
    path = os.path.join(STATE_DIR, CREDENTIALS_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        return {k: str(v) for k, v in raw.items() if isinstance(v, str)}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def clear_credentials() -> None:
    """删除所有持久化凭证。"""
    path = os.path.join(STATE_DIR, CREDENTIALS_FILE)
    if os.path.exists(path):
        os.remove(path)


def has_credentials() -> bool:
    """检查是否已有持久化凭证。"""
    return bool(load_credentials().get("token"))


def load_context_token() -> str:
    """读取持久化的 context_token（从 _poll_context.py 保存的）。

    Returns:
        context_token 字符串，若文件不存在或为空则返回 ""。
    """
    path = os.path.join(STATE_DIR, "context_token.json")
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return str(raw.get("context_token", "") or "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def save_context_token(ctx: str, from_user: str = "") -> str:
    """保存 context_token 到磁盘。

    Args:
        ctx: context_token 字符串
        from_user: 来源用户 ID

    Returns:
        保存的文件路径
    """
    _ensure_dir(STATE_DIR)
    data = {"context_token": ctx, "from_user": from_user}
    path = os.path.join(STATE_DIR, "context_token.json")
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.name != "nt":
            os.chmod(tmp, _PRIVATE_FILE_MODE)
        os.replace(tmp, path)
        if os.name != "nt":
            os.chmod(path, _PRIVATE_FILE_MODE)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return path
