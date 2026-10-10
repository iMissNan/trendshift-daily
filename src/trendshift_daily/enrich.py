"""F3 元数据 + F8 硬过滤(纯逻辑部分)。HTTP 调用由 fetch_repo_meta 负责,单独成函数便于替换。"""
import json
import urllib.request
from datetime import date, datetime


def parse_repo_meta(raw):
    """只保留设计书定义的字段,丢弃其余。pushed_at 归一为 YYYY-MM-DD。"""
    pushed = raw.get("pushed_at")
    pushed = pushed[:10] if pushed else None
    return {
        "description": raw.get("description") or "",
        "language": raw.get("language") or "",
        "stars": raw.get("stargazers_count"),
        "topics": raw.get("topics", []),
        "pushed_at": pushed,
        "archived": raw.get("archived"),
        "html_url": raw.get("html_url"),
    }


def hard_stale_verdict(meta, today, stale_days=730):
    """F8 硬过滤。返回 (标签, 理由) 或 None。数据缺失一律不触发(防误杀)。"""
    if meta.get("archived") is True:
        return ("不推荐", "已归档")
    pushed = meta.get("pushed_at")
    if not pushed:
        return None
    age = (today - datetime.strptime(pushed, "%Y-%m-%d").date()).days
    if age > stale_days:
        return ("不推荐", "两年以上未更新")
    return None


def fetch_repo_meta(full_name, timeout=20):
    """F3:GitHub 公开只读接口,无需鉴权。失败返回 {'error': ...},不抛出。"""
    h = {"User-Agent": "trendshift-daily", "Accept": "application/vnd.github+json"}
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(f"https://api.github.com/repos/{full_name}", headers=h),
            timeout=timeout)
        return parse_repo_meta(json.loads(r.read()))
    except Exception as e:  # noqa: BLE001 — 失败要记录,不能崩掉整批
        return {"error": str(e)[:160]}
