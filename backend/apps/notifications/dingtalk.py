"""
钉钉群机器人 Webhook 客户端。

文档: https://open.dingtalk.com/document/orgapp/custom-bot-send-message
"""

import base64
import hashlib
import hmac
import time
import urllib.parse

import requests


class DingTalkClient:
    """钉钉群机器人 Webhook 客户端。

    支持三种安全设置:
    - 无安全设置（仅 webhook_url）
    - 加签（webhook_url + secret）
    - 自定义关键词（在消息内容中包含关键词即可，客户端不处理）

    Usage:
        client = DingTalkClient(webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx")
        client.send_markdown(title="告警", text="内容", at_user_ids=["user123"])
    """

    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    def _sign(self) -> tuple:
        """HMAC-SHA256 加签。

        Returns:
            (timestamp, sign) 元组。无 secret 时返回 ("", "")。
        """
        if not self.secret:
            return "", ""

        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{self.secret}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(
            secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def _post(self, payload: dict) -> dict:
        """发送 POST 请求到钉钉 Webhook。

        Returns:
            钉钉 API 响应 dict，包含 errcode 和 errmsg。
        """
        url = self.webhook_url
        timestamp, sign = self._sign()
        if timestamp and sign:
            url = f"{url}&timestamp={timestamp}&sign={sign}"

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"errcode": -1, "errmsg": str(e)}

    def send_markdown(
        self,
        title: str,
        text: str,
        at_user_ids: list[str] | None = None,
        at_mobiles: list[str] | None = None,
        is_at_all: bool = False,
    ) -> dict:
        """发送 Markdown 消息。

        Args:
            title: 消息标题（显示在会话列表）。
            text: Markdown 格式的消息内容。
            at_user_ids: 要 @ 的钉钉 UserID 列表。
            at_mobiles: 要 @ 的手机号列表。
            is_at_all: 是否 @所有人。

        Returns:
            {"errcode": 0, "errmsg": "ok"} 表示成功。
        """
        at_user_ids = at_user_ids or []
        at_mobiles = at_mobiles or []

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text,
            },
            "at": {
                "atUserIds": at_user_ids,
                "atMobiles": at_mobiles,
                "isAtAll": is_at_all,
            },
        }
        return self._post(payload)

    def send_text(
        self,
        content: str,
        at_user_ids: list[str] | None = None,
        at_mobiles: list[str] | None = None,
        is_at_all: bool = False,
    ) -> dict:
        """发送纯文本消息。

        Args:
            content: 文本内容。
            at_user_ids: 要 @ 的钉钉 UserID 列表。
            at_mobiles: 要 @ 的手机号列表。
            is_at_all: 是否 @所有人。

        Returns:
            {"errcode": 0, "errmsg": "ok"} 表示成功。
        """
        at_user_ids = at_user_ids or []
        at_mobiles = at_mobiles or []

        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
            "at": {
                "atUserIds": at_user_ids,
                "atMobiles": at_mobiles,
                "isAtAll": is_at_all,
            },
        }
        return self._post(payload)
