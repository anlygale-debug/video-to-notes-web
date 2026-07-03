#!/usr/bin/env python3
"""企业微信群机器人消息发送 — 通过 Webhook 给微信群发消息"""

import requests
import sys

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0283b64b-0f0a-44d5-b72c-7f050acdbd6e"


def send_text(content):
    resp = requests.post(WEBHOOK_URL, json={
        "msgtype": "text",
        "text": {"content": content},
    }).json()
    if resp.get("errcode") == 0:
        print("发送成功")
    else:
        print(f"发送失败: {resp.get('errmsg', resp)}")


def send_markdown(content):
    resp = requests.post(WEBHOOK_URL, json={
        "msgtype": "markdown",
        "markdown": {"content": content},
    }).json()
    if resp.get("errcode") == 0:
        print("发送成功")
    else:
        print(f"发送失败: {resp.get('errmsg', resp)}")


def main():
    if len(sys.argv) < 2:
        print("用法: python wechat_send.py <消息内容> [--markdown]")
        print("示例: python wechat_send.py 'hello world'")
        print("      python wechat_send.py '## 标题\n- 内容' --markdown")
        sys.exit(1)

    msg = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else ""

    if fmt == "--markdown":
        send_markdown(msg)
    else:
        send_text(msg)


if __name__ == "__main__":
    main()
