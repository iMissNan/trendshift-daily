import json
import os
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

data_root = "/home/linxuan/data/trendshift"
repos_meta = json.load(open(f"{data_root}/meta-2026-10-10.json"))
notes_path = f"{data_root}/notes-2026-10-10.json"
notes = json.load(open(notes_path)) if os.path.exists(notes_path) else {}

env_file = os.path.expanduser("~/.hermes/.env")
env = {}
for line in open(env_file):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k] = v.strip('"').strip("'")

api_key = env.get("HERMES_CUSTOM_HOME_NANSHARK_CCWU_CC_20128_API_KEY", "")
endpoint = "http://127.0.0.1:20128/v1/chat/completions"
model = "yangmao"

to_enrich = []
for repo, meta in repos_meta.items():
    curr = notes.get(repo, {})
    desc = curr.get("what_it_is", "")
    has_cn = any("\u4e00" <= c <= "\u9fff" for c in desc)
    if not has_cn or len(desc) < 20 or "开源项目" in desc:
        to_enrich.append(repo)

print(f"Total to enrich: {len(to_enrich)}")

def analyze_one(repo):
    curr = notes.get(repo, {})
    meta = repos_meta[repo]
    desc = meta.get("description") or "无官方简介"
    stars = meta.get("stargazers_count", 0)
    topics = ", ".join(meta.get("topics") or [])
    
    prompt = f"""请分析开源项目 {repo}。
官方简介: {desc}
Star 数量: {stars}
Topics 标签: {topics}

【严格要求】
1. 严禁敷衍，严禁说'这是一个开源项目'、'这是一个仓库'。
2. 必须用专业、地道、通俗的中文回答，准确指出它是干什么用的、核心实现了什么功能机制与技术特色。
3. 输出纯 JSON，包含且仅包含以下 3 个键：
{{
  "what_it_is": "清晰描述这个项目是做什么的、实现了什么核心功能与技术特色(40~75字)",
  "for_us": "从家庭服务器运维/AI Agent常驻/CTF逆向/开发提效角度评估对我们的针对性价值(30~55字)",
  "evidence": "推导依据(如 meta.description、Topics 等)"
}}
只输出纯 JSON，严禁输出任何 markdown 标记。"""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    for attempt in range(2):
        try:
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"): content = content.split("\n", 1)[1]
                if content.endswith("```"): content = content.rsplit("\n", 1)[0]
                parsed = json.loads(content)
                what = parsed.get("what_it_is", "").strip()
                if what and len(what) >= 20 and "开源项目" not in what:
                    return repo, {
                        "what_it_is": what,
                        "for_us": parsed.get("for_us", "保持通用技术跟进与关注"),
                        "evidence": parsed.get("evidence", "meta.description"),
                        "streak": curr.get("streak", 1)
                    }
        except Exception as e:
            time.sleep(1)
            
    return repo, None

success_count = 0
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(analyze_one, r): r for r in to_enrich}
    for future in as_completed(futures):
        repo, result = future.result()
        if result:
            notes[repo] = result
            success_count += 1
            print(f"[{success_count}/{len(to_enrich)}] {repo} OK")
        else:
            print(f"Failed {repo}")

json.dump(notes, open(notes_path, "w"), ensure_ascii=False, indent=2)
print(f"Batch enrichment complete: {success_count}/{len(to_enrich)} succeeded.")
