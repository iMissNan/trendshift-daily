"""Trendshift 日报 · 飞书通知与回读验证器。
实现 F11(推送与回读)、F12(失败告警)。
"""
import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple

BASE_URL = "https://open.feishu.cn"

def get_tenant_access_token(app_id: str, app_secret: str) -> Optional[str]:
    """通过飞书自建应用凭据获取 tenant_access_token。"""
    url = f"{BASE_URL}/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    payload = {"app_id": app_id, "app_secret": app_secret}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0:
                return data.get("tenant_access_token")
    except Exception:
        pass
    return None

def send_feishu_card(
    chat_id: str,
    card: Dict[str, Any],
    token: str
) -> Tuple[bool, Optional[str], str]:
    """向指定 chat_id 投递飞书 interactive 卡片并返回 message_id。"""
    url = f"{BASE_URL}/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("code") == 0:
                msg_id = (res.get("data") or {}).get("message_id")
                return True, msg_id, "success"
            return False, None, res.get("msg", "unknown error")
    except Exception as e:
        return False, None, str(e)

def verify_message_delivered(message_id: str, token: str) -> Tuple[bool, str]:
    """回读消息核验真实投递状态 (真金白银无假绿灯)。"""
    url = f"{BASE_URL}/open-apis/im/v1/messages/{message_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("code") == 0:
                data = res.get("data") or {}
                items = data.get("items") or []
                if items:
                    msg = items[0]
                    # 核验未被撤回且存在
                    if not msg.get("deleted", False):
                        return True, "verified_delivered"
            return False, f"verify failed: {res.get('msg')}"
    except Exception as e:
        return False, str(e)

def send_failure_alert(
    chat_id: str,
    stage: str,
    reason: str,
    token: str
) -> Tuple[bool, Optional[str]]:
    """发生故障时主动向群内推送告警，绝不沉默。"""
    alert_card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "⚠️ Trendshift 日报 · 本次无产出告警"
            },
            "template": "red"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": (
                    f"**故障环节：**`{stage}`\n"
                    f"**原因详情：**{reason}\n\n"
                    f"<font color='grey'>家庭服务器看门狗自动拦截上报 · 保持透明不沉默</font>"
                )
            }
        ]
    }
    ok, msg_id, _ = send_feishu_card(chat_id, alert_card, token)
    return ok, msg_id
