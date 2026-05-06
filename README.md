# wechat-ilink-push
Co-Contributors: hwu668 · DeepSeek

**零第三方依赖的微信 iLink Bot 推送工具。**

基于微信官方 ClawBot 插件的 iLink HTTP 协议，直接调用 5 个开放接口。
不引入任何第三方 SDK，全部代码 ~400 行，可逐行审计。

## ✨ 特性

- 🔐 **安全透明** —— 全部源码 ~400 行 Python，无黑盒、无遥测
- 📡 **仅调微信官方 API** —— 所有请求只发到 `ilinkai.weixin.qq.com`
- 💾 **凭证本地加密存储** —— `~/.ilink_push/credentials.json`，权限 0o600
- 📤 **文本 + 文件发送** —— 支持发消息、发文件（.md / .pdf / 图片）
- 🤖 **独立运行** —— 可配合 cron 定时推送；也可作为 Python 库被其他项目调用
- 🪶 **唯一依赖** —— `httpx`（Python HTTP 客户端，数万 star 的成熟项目）

## 📦 安装

```bash
git clone https://github.com/hwu668/wechat-ilink-push.git
cd wechat-ilink-push
pip install -r requirements.txt
```

唯一依赖：`httpx`

## 🚀 快速开始

### 1. 扫码登录（一次性）

```bash
python login.py
```

终端会打印一个二维码链接，在浏览器中打开，用**微信扫码**，手机上确认登录。

登录成功后凭证保存在 `~/.ilink_push/credentials.json`，后续无需重复登录。

### 2. 推送消息

```bash
# 发送文本
python push.py "Hello from Python!"

# 发送文件
python push.py --file report.md

# 发送文件 + 文字说明
python push.py --file report.md -m "📊 今日报告"

# 从管道读取
echo "Hello" | python push.py
```

### 3. 推送财经日报（配合 advanced_investment_strategy）

```bash
# 生成日报 + 推送
python send_digest.py

# 生成并保存 md + 推送
python send_digest.py --save
```

### 4. 作为 Python 库使用

```python
import asyncio
from ilink import get_client

async def main():
    client = get_client()  # 自动读取 ~/.ilink_push/credentials.json
    await client.send_message("Hello from code!")
    await client.close()

asyncio.run(main())
```

## ⏰ 定时推送（cron）

每天早上 8:00 推送财经日报：

```bash
crontab -e
```

```
0 8 * * 1-5 cd /home/pi/wechat-ilink-push && python send_digest.py >> /tmp/digest_push.log 2>&1
```

## 🔒 安全性

| 项目 | 说明 |
|------|------|
| 网络请求 | 所有请求仅发往 `https://ilinkai.weixin.qq.com`（腾讯服务器） |
| 凭证存储 | `~/.ilink_push/credentials.json`，文件权限 0o600（仅本用户可读） |
| 无第三方 | 不经过任何中间服务器，不依赖任何第三方 SDK |
| 协议 | 基于微信官方 ClawBot 插件开放的 iLink HTTP 协议 |
| 权限范围 | Bot 有独立身份，**不能**读取你的微信聊天记录、好友列表 |

## 📁 文件结构

```
wechat-ilink-push/
├── ilink/
│   ├── __init__.py    # 包导出 + get_client()
│   ├── client.py      # HTTP 客户端 (send_message, send_file)
│   ├── auth.py        # 扫码登录流程
│   └── storage.py     # Token 本地持久化
├── login.py           # CLI: 扫码登录
├── push.py            # CLI: 推送消息/文件
├── send_digest.py     # 财经日报推送
├── requirements.txt   # httpx
└── README.md
```

## 📄 License

MIT
