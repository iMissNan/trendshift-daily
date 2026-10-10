"""Trendshift 日报 · 全链路流水线编排器 (Pipeline)。
实现 F1~F13 全链路生命周期：自检 -> 抓取 -> 元数据 -> 研判 -> 渲染 -> 投递 -> 回读 -> 告警。
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

from trendshift_daily.analyzer import (
    is_hard_rejected,
    determine_tag,
    validate_analysis_result,
    build_analysis_prompt,
    query_10router_analysis
)
from trendshift_daily.card_builder import build_feishu_cards
from trendshift_daily.notifier import (
    get_tenant_access_token,
    send_feishu_card,
    verify_message_delivered,
    send_failure_alert
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trendshift-daily")

def load_config(config_path: str) -> Dict[str, Any]:
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_self_check(config: Dict[str, Any]) -> Tuple[bool, str]:
    """启动前链路自检 (F13)。"""
    # 1. 检查环境变量文件
    env_file = os.path.expanduser(config["feishu"]["env_file"])
    if not os.path.exists(env_file):
        return False, f"飞书环境变量文件不存在: {env_file}"
        
    # 2. 检查数据落盘根目录
    data_root = os.path.expanduser(config["data_root"])
    os.makedirs(data_root, exist_ok=True)
    
    return True, "self_check_passed"

def run_pipeline(config_path: str, dry_run: bool = False, target_day: str = "") -> bool:
    config = load_config(config_path)
    day = target_day or datetime.now().strftime("%Y-%m-%d")
    
    logger.info("启动 Trendshift 日报处理流程，目标日期: %s (dry_run=%s)", day, dry_run)
    
    ok, check_msg = run_self_check(config)
    if not ok:
        logger.error("自检失败: %s", check_msg)
        return False

    data_root = Path(os.path.expanduser(config["data_root"]))
    raw_dir = data_root / "raw" / day
    manifest_path = raw_dir / "manifest.json"
    
    if not manifest_path.exists():
        logger.error("未找到当天榜单快照清单: %s", manifest_path)
        return False
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    raw_boards = {}
    for board_key, board_meta in manifest.get("boards", {}).items():
        board_file = Path(board_meta["file"])
        if board_file.exists():
            with open(board_file, "r", encoding="utf-8") as f:
                raw_boards[board_key] = json.load(f).get("items", [])
                
    meta_file = data_root / f"meta-{day}.json"
    if not meta_file.exists():
        # 如果当天还没有 meta，回退到昨天或默认
        logger.warning("未找到 meta 文件: %s", meta_file)
        repos_meta = {}
    else:
        with open(meta_file, "r", encoding="utf-8") as f:
            repos_meta = json.load(f)

    # 加载已有的 notes/分析
    notes_file = data_root / f"notes-{day}.json"
    existing_notes = {}
    if notes_file.exists():
        with open(notes_file, "r", encoding="utf-8") as f:
            existing_notes = json.load(f)

    # 构建精选条目
    curated_items = []
    must_count = 0
    rec_count = 0
    watch_count = 0
    rej_count = 0
    
    featured_cap = config.get("card", {}).get("featured_cap", 25)
    must_daily_cap = config.get("tagging", {}).get("must_daily_cap", 3)
    
    for repo, meta in repos_meta.items():
        rejected, reject_reason = is_hard_rejected(meta, stale_days=config["github"]["stale_days"])
        note = existing_notes.get(repo, {})
        
        analysis = {
            "what_it_is": note.get("what_it_is") or meta.get("description") or "开源项目",
            "for_us": note.get("for_us") or "保持技术关注与跟踪",
            "evidence": note.get("evidence") or "meta.description"
        }
        
        tag = determine_tag(meta, analysis)
        if rejected:
            rej_count += 1
            tag = "不推荐"
        elif tag == "必看":
            if must_count < must_daily_cap:
                must_count += 1
            else:
                tag = "推荐"
                rec_count += 1
        elif tag == "推荐":
            rec_count += 1
        else:
            watch_count += 1
            
        curated_items.append({
            "repo": repo,
            "tag": tag,
            "streak": note.get("streak", 1),
            "what_it_is": analysis["what_it_is"],
            "for_us": analysis["for_us"],
            "evidence": analysis["evidence"],
            "rejected": rejected,
            "reject_reason": reject_reason
        })
        
    # 严格收敛精选区：非必看全部取消，仅保留真正高价值的【必看】项目
    displayed_curated = [item for item in curated_items if item["tag"] == "必看"][:featured_cap]
    
    summary = {
        "fetched_at": manifest.get("fetched_at", datetime.now().isoformat()),
        "total_repos": len(repos_meta),
        "counts": {
            "must": must_count,
            "rec": rec_count,
            "watch": watch_count,
            "rejected": rej_count
        }
    }
    
    cards = build_feishu_cards(
        day=day,
        summary=summary,
        curated=displayed_curated,
        raw_boards=raw_boards,
        notes=existing_notes
    )
    
    logger.info("卡片组装完成，生成 %d 页卡片", len(cards))
    
    # 落盘卡片产物
    output_card_path = data_root / f"card-{day}.json"
    with open(output_card_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    logger.info("卡片 JSON 已保存至: %s", output_card_path)

    if dry_run:
        logger.info("[Dry Run] 模式，跳过真实飞书投递与回读。")
        return True
        
    # 读取环境变量飞书凭据
    env_file = os.path.expanduser(config["feishu"]["env_file"])
    app_id = ""
    app_secret = ""
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                if k == "FEISHU_APP_ID":
                    app_id = v.strip("'\"")
                elif k == "FEISHU_APP_SECRET":
                    app_secret = v.strip("'\"")
                    
    token = get_tenant_access_token(app_id, app_secret)
    if not token:
        logger.error("获取飞书 Tenant Token 失败！")
        return False
        
    chat_id = config["feishu"]["chat_id"]
    for idx, card in enumerate(cards, 1):
        ok, msg_id, err = send_feishu_card(chat_id, card, token)
        if not ok or not msg_id:
            logger.error("第 %d 页卡片投递失败: %s", idx, err)
            send_failure_alert(chat_id, f"投递卡片 (第 {idx} 页)", err, token)
            return False
            
        logger.info("第 %d 页投递成功，message_id=%s，执行回读核验...", idx, msg_id)
        verified, ver_msg = verify_message_delivered(msg_id, token)
        if not verified:
            logger.error("回读核验失败: %s", ver_msg)
            return False
        logger.info("第 %d 页回读核验成功: %s", idx, ver_msg)
        
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trendshift 日报全链路处理")
    parser.add_argument("--config", default="config/trendshift.yaml", help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，不真实发送飞书")
    parser.add_argument("--day", default="", help="指定日期 YYYY-MM-DD")
    args = parser.parse_args()
    
    success = run_pipeline(config_path=args.config, dry_run=args.dry_run, target_day=args.day)
    sys.exit(0 if success else 1)
