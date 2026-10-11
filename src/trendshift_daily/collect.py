"""F1 榜单采集核心逻辑与执行入口。
使用 Playwright 无头抓取 Trendshift 五大榜单，保序去重，生成快照与 manifest.json。
"""
import hashlib
import json
import logging
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trendshift-collect")

TZ_CST = timezone(timedelta(hours=8))

def dedupe_keep_order(items: List[str]) -> List[str]:
    """按出现顺序去重,只删完全重复的非空条目,不删任何不同条目。"""
    seen = set()
    out = []
    for s in items:
        s = (s or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out

def check_board(board: Dict[str, Any], floor: int = 20) -> bool:
    """F1 校验:有 error 或条目数低于下限,判该榜失败。"""
    if "error" in board:
        return False
    return board.get("count", 0) >= floor

def compute_sha256(filepath: str) -> str:
    """计算文件 SHA-256 哈希值。"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def scrape_board(page, base: str, path: str, scroll_rounds: int = 6, max_retries: int = 2) -> Tuple[List[str], int]:
    """F1:用已打开的 Playwright page 抓一个榜单,返回 (去重列表, 原始链接数)。带重试机制。"""
    for attempt in range(max_retries + 1):
        try:
            page.goto(base + path, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(scroll_rounds):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
            raw = page.eval_on_selector_all(
                'a[href^="/repositories/"]',
                "els => els.map(a => (a.innerText||'').trim().replace(/\\s+/g,' '))"
            )
            return dedupe_keep_order(raw), len(raw)
        except Exception as e:
            if attempt < max_retries:
                logger.warning("抓取 %s 超时或异常: %s, 正在进行第 %d 次重试...", path, e, attempt + 1)
                page.wait_for_timeout(3000)
            else:
                raise e
    return [], 0

def run_collect(config_path: str, target_day: str = "") -> Tuple[bool, str, Dict[str, Any]]:
    """执行 5 大榜单采集与落盘全流程。"""
    import yaml
    from playwright.sync_api import sync_playwright

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    src_cfg = cfg.get("source", {})
    base_url = src_cfg.get("base", "https://trendshift.io")
    boards = src_cfg.get("boards", {
        "daily": "/",
        "weekly": "/weekly",
        "monthly": "/monthly",
        "yearly": "/yearly",
        "github_trending": "/github-trending-repositories"
    })
    scroll_rounds = src_cfg.get("scroll_rounds", 6)
    min_items = src_cfg.get("board_min_items", 20)
    data_root = Path(os.path.expanduser(cfg.get("data_root", "~/data/trendshift")))

    now = datetime.now(TZ_CST)
    day = target_day or now.strftime("%Y-%m-%d")
    out_dir = data_root / "raw" / day
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "fetched_at": now.isoformat(),
        "source": base_url,
        "boards": {}
    }
    all_unique_repos = []
    seen_repos = set()

    logger.info("开始执行 Trendshift 榜单采集: 目标日期 %s, 输出目录: %s", day, out_dir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for name, path in boards.items():
            logger.info("正在抓取榜单: %s (%s)", name, path)
            try:
                items, raw_n = scrape_board(page, base_url, path, scroll_rounds)
                board_file = out_dir / f"{name}.json"
                with open(board_file, "w", encoding="utf-8") as bf:
                    json.dump({
                        "board": name,
                        "path": path,
                        "raw_links": raw_n,
                        "items": items
                    }, bf, ensure_ascii=False, indent=2)

                sha = compute_sha256(str(board_file))
                manifest["boards"][name] = {
                    "count": len(items),
                    "raw_links": raw_n,
                    "sha256": sha,
                    "file": str(board_file)
                }
                logger.info("榜单 %s 抓取完成: %d 条 (原始 %d)", name, len(items), raw_n)

                # 收集全量去重仓库名
                for it in items:
                    repo_name = it.split()[0].strip()
                    if repo_name and repo_name not in seen_repos:
                        seen_repos.add(repo_name)
                        all_unique_repos.append(repo_name)

            except Exception as e:
                logger.error("抓取榜单 %s 失败: %s", name, e)
                manifest["boards"][name] = {"error": str(e)[:200]}
        browser.close()

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)
    logger.info("manifest.json 已生成: %s", manifest_path)

    # 保存当日去重仓库列表 repos-YYYY-MM-DD.json
    repos_file = data_root / f"repos-{day}.json"
    with open(repos_file, "w", encoding="utf-8") as rf:
        json.dump(all_unique_repos, rf, ensure_ascii=False, indent=2)
    logger.info("去重仓库列表已生成 (%d 个): %s", len(all_unique_repos), repos_file)

    # 校验每个榜单是否达标
    bad_boards = []
    for k, v in manifest["boards"].items():
        if not check_board(v, floor=min_items):
            bad_boards.append(k)

    if bad_boards:
        msg = f"以下榜单未达标或抓取失败: {', '.join(bad_boards)}"
        logger.error(msg)
        return False, msg, manifest

    return True, "OK", manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trendshift 榜单采集")
    parser.add_argument("--config", default="config/trendshift.yaml", help="配置文件路径")
    parser.add_argument("--day", default="", help="指定日期 YYYY-MM-DD")
    args = parser.parse_args()

    success, msg, manifest_data = run_collect(args.config, args.day)
    print(f"[{'SUCCESS' if success else 'FAILURE'}] {msg}")
    sys.exit(0 if success else 1)
