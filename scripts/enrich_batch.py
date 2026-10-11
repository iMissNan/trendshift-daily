import json
import os
import sys
from pathlib import Path

# 将项目 src 加入 sys.path 确保可导入 trendshift_daily
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import argparse
import urllib.request
from datetime import datetime, timezone, timedelta

TZ_CST = timezone(timedelta(hours=8))

def enrich_meta_and_notes(day: str = "", data_root_path: str = "~/data/trendshift", limit_enrich: int = 25):
    target_day = day or datetime.now(TZ_CST).strftime("%Y-%m-%d")
    data_root = os.path.expanduser(data_root_path)
    
    # 1. 尝试读取当日 meta，若无则尝试从 repos 动态拉取或继承
    repos_file = f"{data_root}/repos-{target_day}.json"
    meta_file = f"{data_root}/meta-{target_day}.json"
    notes_file = f"{data_root}/notes-{target_day}.json"
    
    repos = []
    if os.path.exists(repos_file):
        repos = json.load(open(repos_file, encoding="utf-8"))
    
    # 读取历史已有 notes 作为基础缓存
    notes = {}
    if os.path.exists(notes_file):
        notes = json.load(open(notes_file, encoding="utf-8"))
    else:
        # 回退继承昨天或前天的 notes
        yesterday = (datetime.strptime(target_day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        y_notes_file = f"{data_root}/notes-{yesterday}.json"
        if os.path.exists(y_notes_file):
            notes = json.load(open(y_notes_file, encoding="utf-8"))
            print(f"继承昨日研判缓存 ({yesterday}): {len(notes)} 条")

    # 读取已有 meta 或继承昨日
    repos_meta = {}
    if os.path.exists(meta_file):
        repos_meta = json.load(open(meta_file, encoding="utf-8"))
    else:
        yesterday = (datetime.strptime(target_day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        y_meta_file = f"{data_root}/meta-{yesterday}.json"
        if os.path.exists(y_meta_file):
            repos_meta = json.load(open(y_meta_file, encoding="utf-8"))
            print(f"继承昨日元数据缓存 ({yesterday}): {len(repos_meta)} 条")

    # 对 repos 中缺失 meta 的项目调用 GitHub 公开 API 增量获取
    from trendshift_daily.enrich import fetch_repo_meta
    missing_meta = [r for r in repos if r not in repos_meta or not repos_meta[r].get("description")]
    if missing_meta:
        print(f"检测到 {len(missing_meta)} 个仓库缺失元数据，开始增量拉取 GitHub Meta...")
        for r in missing_meta:
            m = fetch_repo_meta(r)
            if "error" not in m:
                repos_meta[r] = m
        json.dump(repos_meta, open(meta_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"元数据已更新落盘: {meta_file} ({len(repos_meta)} 条)")
    else:
        if not os.path.exists(meta_file) and repos_meta:
            json.dump(repos_meta, open(meta_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 10Router 研判
    env_file = os.path.expanduser("~/.hermes/.env")
    env = {}
    if os.path.exists(env_file):
        for line in open(env_file, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"').strip("'")

    api_key = env.get("HERMES_CUSTOM_HOME_NANSHARK_CCWU_CC_20128_API_KEY", "")
    endpoint = "http://127.0.0.1:20128/v1/chat/completions"
    model = "yangmao"

    # 优先筛选出尚未研判过的新上榜仓库
    candidates = [r for r in repos if r in repos_meta and (r not in notes or not notes[r].get("what_it_is"))]
    if len(candidates) < limit_enrich:
        # 如果未研判的不满 limit，补齐排名前列的项目
        additional = [r for r in repos if r in repos_meta and r not in candidates][:limit_enrich - len(candidates)]
        candidates.extend(additional)

    candidates = candidates[:limit_enrich]
    print(f"目标日期 {target_day}：开始 10Router 深度中文结构化研判 (共 {len(candidates)} 个候选)...")

    count = 0
    for repo in candidates:
        curr = notes.get(repo, {})
        meta = repos_meta.get(repo, {})
        desc = meta.get("description") or meta.get("desc") or "无官方简介"
        stars = meta.get("stargazers_count") or meta.get("stars") or 0
        topics = ", ".join(meta.get("topics") or [])

        prompt = f"""请分析开源项目 {repo}。
官方简介: {desc}
Star 数量: {stars}
Topics 标签: {topics}

请用专业、通俗、流畅的中文输出合法 JSON，包含以下 3 个键：
{{
  "what_it_is": "清晰描述这个项目是做什么的、实现了什么核心功能与技术特色(40~65字)",
  "for_us": "从家庭服务器运维/AI Agent常驻/CTF逆向/开发提效角度评估对我们的针对性价值(30~50字)",
  "evidence": "推导依据(如 meta.description、Topics 等)"
}}
只输出纯 JSON，严禁输出任何 markdown 格式标记。"""

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        try:
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("\n", 1)[0]
                parsed = json.loads(content)

                notes[repo] = {
                    "what_it_is": parsed.get("what_it_is", desc),
                    "for_us": parsed.get("for_us", "保持技术关注"),
                    "evidence": parsed.get("evidence", "meta.description"),
                    "streak": curr.get("streak", 1)
                }
                count += 1
                print(f"[{count}/{len(candidates)}] {repo} enriched OK")
        except Exception as e:
            print(f"Failed {repo}: {e}")

    json.dump(notes, open(notes_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"研判提纯完毕，已落盘至 {notes_file} (总计覆盖: {len(notes)} 条)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="10Router 中文深度研判与元数据增量同步")
    parser.add_argument("--day", default="", help="指定日期 YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=25, help="单次研判数量上限")
    args = parser.parse_args()

    enrich_meta_and_notes(day=args.day, limit_enrich=args.limit)
