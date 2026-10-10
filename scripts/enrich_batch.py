import json
import os
import urllib.request

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

# 选取前 25 个精选候选项目进行 10Router 深度中文结构化分析提纯
curated_candidates = list(repos_meta.keys())[:25]
print("Starting 10Router deep batch enrichment for 25 repos...")

count = 0
for repo in curated_candidates:
    curr = notes.get(repo, {})
    meta = repos_meta[repo]
    desc = meta.get("description") or "无官方简介"
    stars = meta.get("stargazers_count", 0)
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
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
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
            print(f"[{count}/25] {repo} enriched OK")
    except Exception as e:
        print(f"Failed {repo}: {e}")

json.dump(notes, open(notes_path, "w"), ensure_ascii=False, indent=2)
print("Enrichment complete. Total enriched:", count)
