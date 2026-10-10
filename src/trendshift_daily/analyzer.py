"""Trendshift 日报 · 结构化研判与规则引擎。
实现 F5(结构化分析)、F6(标签判定)、F8(过时一票否决)、F9(状态机缓存)。
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional

def is_hard_rejected(meta: Dict[str, Any], stale_days: int = 730) -> Tuple[bool, str]:
    """硬否决检查:已归档 或 >stale_days 无代码更新。"""
    if meta.get("archived") is True:
        return True, "仓库已于历史归档（Archived），触发一票否决"
    
    pushed_at_str = meta.get("pushed_at")
    if pushed_at_str:
        try:
            pushed_dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            delta = now_dt - pushed_dt
            if delta.days > stale_days:
                return True, f"最后更新于 {delta.days} 天前，超 {stale_days} 天无维护，触发一票否决"
        except Exception:
            pass
            
    return False, ""

def validate_analysis_result(data: Dict[str, Any]) -> Tuple[bool, str]:
    """严查依凭与中文描述质量，严禁无源脑补或几个单词敷衍。"""
    if not isinstance(data, dict):
        return False, "分析结果必须是字典/JSON对象"
    
    what = data.get("what_it_is", "").strip()
    if not what or len(what) < 10:
        return False, "项目简介过短或缺失，必须清晰说明项目是做什么的、实现了什么核心功能"
        
    for_us = data.get("for_us", "").strip()
    if not for_us or len(for_us) < 8:
        return False, "缺失对我们的价值分析（for_us）"
        
    evidence = data.get("evidence", "").strip()
    if not evidence or evidence.lower() in ("none", "null", "无", "看不出"):
        return False, "缺失有效的依据来源（evidence）"
        
    return True, ""

def determine_tag(
    meta: Dict[str, Any],
    analysis: Dict[str, Any],
    streak_days: int = 1,
    recent_days_must: int = 90,
    recent_days_rec: int = 180
) -> str:
    """标签判定规则引擎:必看 / 推荐 / 关注 / 观望 / 注意 / 不推荐。"""
    rejected, _ = is_hard_rejected(meta)
    if rejected:
        return "不推荐"
        
    for_us = analysis.get("for_us", "")
    what = analysis.get("what_it_is", "")
    evidence = analysis.get("evidence", "")
    
    if not evidence or "信息不足" in for_us or "信息不足" in what:
        return "观望"
        
    is_fresh_must = False
    is_fresh_rec = False
    pushed_at_str = meta.get("pushed_at")
    if pushed_at_str:
        try:
            pushed_dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - pushed_dt
            is_fresh_must = (delta.days <= recent_days_must)
            is_fresh_rec = (delta.days <= recent_days_rec)
        except Exception:
            pass

    keywords_must = ("家庭服务器", "底座", "hermes", "逆向", "ctf", "核心依赖")
    if any(k in for_us.lower() for k in keywords_must) and is_fresh_must:
        return "必看"
        
    keywords_rec = ("替代品", "推荐", "储备", "工具箱", "高星", "利器", "重要组件")
    if (any(k in for_us.lower() for k in keywords_rec) or streak_days >= 3) and is_fresh_rec:
        return "推荐"
        
    return "关注"

def build_analysis_prompt(repo: str, meta: Dict[str, Any], readme_head: str = "") -> str:
    """构造面向 10Router 的强制中文结构化研判提示词。"""
    desc = meta.get("description") or "无官方英文简介"
    stars = meta.get("stargazers_count", 0)
    topics = ", ".join(meta.get("topics") or [])
    
    return f"""你是一位精通软件架构与开源生态的高级技术专家。请对 GitHub 仓库 {repo} 进行深度研判。
已知客观事实:
- 官方简介: {desc}
- Star 数量: {stars}
- Topics 标签: {topics}
- README 摘要(前置内容):
{readme_head[:2500]}

【强制要求】
1. 严禁用几个单词敷衍，严禁说'这是一个开源项目'这类空话。
2. 必须用通俗、严谨、流畅的中文回答。
3. 输出纯 JSON 格式，包含且仅包含以下 3 个字段:
{{
  "what_it_is": "清晰阐述该项目是做什么的、实现了什么核心功能与技术亮点(40~70字)",
  "for_us": "从家庭服务器自动化、常驻Agent运维、CTF逆向/安全、或自建媒体服务角度，评估对我们的针对性价值(30~55字)",
  "evidence": "上述推导的客观依据来源(如 meta.description、Topics、README小节等)"
}}
只输出纯 JSON 字符串，不要带 markdown 标记。
"""

def query_10router_analysis(
    repo: str,
    meta: Dict[str, Any],
    readme_head: str = "",
    endpoint: str = "http://127.0.0.1:20128/v1/chat/completions",
    api_key_env: str = "HERMES_CUSTOM_HOME_NANSHARK_CCWU_CC_20128_API_KEY",
    model: str = "yangmao"
) -> Optional[Dict[str, Any]]:
    """向 10Router 网关发起推理请求并解析纯中文 JSON。"""
    env_file = os.path.expanduser("~/.hermes/.env")
    api_key = os.environ.get(api_key_env, "")
    if not api_key and os.path.exists(env_file):
        for line in open(env_file):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                if k == api_key_env:
                    api_key = v.strip("'\"")

    prompt = build_analysis_prompt(repo, meta, readme_head)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    
    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            parsed = json.loads(content)
            valid, _ = validate_analysis_result(parsed)
            if valid:
                return parsed
    except Exception:
        pass
    return None
