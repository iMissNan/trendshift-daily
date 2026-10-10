"""Trendshift 日报 · 飞书交互卡片渲染器。
实现 F10(卡片渲染与拆页)。附带直接跳转链接、专业中文描述、专属设计感徽章、双列表格折叠抽屉与细粒度拆页。
"""
import json
from typing import Dict, Any, List, Optional

CARD_BYTE_LIMIT = 25000  # 飞书单卡 JSON 保守上限

def format_repo_line(item: Dict[str, Any]) -> str:
    """按规范渲染单个仓库的卡片正文 (高阶设计感标签 + GitHub 超链接 + 全角标点 + 严谨依凭)。"""
    repo = item["repo"]
    url = item.get("url") or f"https://github.com/{repo}"
    tag = item.get("tag", "必看")
    streak = item.get("streak", 1)
    rejected = item.get("rejected", False)
    
    # 飞书 markdown 超链接语法: [标题](url)
    repo_link = f"[{repo}]({url})"
    
    # 设计感视觉标签 (采用 emoji + 醒目排版符号 + 色彩语义化)
    tag_badge_map = {
        "必看": "🔥 <font color='red'>【必看】</font>",
        "推荐": "✨ <font color='green'>【推荐】</font>",
        "关注": "📌 <font color='blue'>【关注】</font>",
        "观望": "🔍 <font color='grey'>【观望】</font>",
        "不推荐": "⚠️ <font color='grey'>【不推荐】</font>"
    }
    tag_badge = tag_badge_map.get(tag, f"【{tag}】")
    
    # 连续上榜设计勋章
    streak_part = f" ` 连续 {streak} 天 ` " if streak > 1 else ""
    
    if rejected:
        reason = item.get("reject_reason", "已归档或超长期停更")
        evidence = item.get("evidence", "GitHub API")
        return (
            f"**~~{repo_link}~~**  {tag_badge}\n"
            f"**状态：**{reason}\n"
            f"<font color='grey'>【依据来源】{evidence}</font>"
        )
    
    what = item.get("what_it_is", "开源工具")
    for_us = item.get("for_us", "保持技术追踪")
    evidence = item.get("evidence", "meta.description")
    
    return (
        f"**{repo_link}**  {tag_badge}{streak_part}\n"
        f"**简介：**{what}\n"
        f"**价值：**{for_us}\n"
        f"<font color='grey'>【依据来源】{evidence}</font>"
    )

def build_collapsible_table_panel(
    title: str,
    items: List[str],
    notes: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """构建双列表格折叠面板，单表超过 15 条自动拆为子抽屉，防单个面板超限。"""
    notes = notes or {}
    chunk_size = 15
    panels = []
    
    if not items:
        return [{
            "tag": "collapsible_panel",
            "expanded": False,
            "header": {
                "title": {"tag": "plain_text", "content": f"{title}（0 条）"}
            },
            "border": {"color": "orange", "corner_radius": "6px"},
            "elements": [{"tag": "markdown", "content": "（本榜无数据）"}]
        }]
        
    for chunk_idx in range(0, len(items), chunk_size):
        chunk_items = items[chunk_idx:chunk_idx + chunk_size]
        table_rows = ["| 仓库名称 | 核心功能简介 |", "| :--- | :--- |"]
        for s in chunk_items:
            repo_name = s.split()[0]
            desc = notes.get(repo_name, {}).get("what_it_is") or "暂无详细简介"
            desc_clean = desc.replace("|", "\\|").replace("\n", " ").strip()
            table_rows.append(f"| [{repo_name}](https://github.com/{repo_name}) | {desc_clean} |")
            
        table_content = "\n".join(table_rows)
        suffix = f" ({chunk_idx+1}~{chunk_idx+len(chunk_items)})" if len(items) > chunk_size else f"（{len(items)} 条）"
        panels.append({
            "tag": "collapsible_panel",
            "expanded": False,
            "header": {
                "title": {"tag": "plain_text", "content": f"{title}{suffix} · 表格速览"}
            },
            "border": {"color": "orange", "corner_radius": "6px"},
            "elements": [{"tag": "markdown", "content": table_content}]
        })
        
    return panels

def build_curated_panel(curated: List[Dict[str, Any]], title_prefix: str = "🌟 小兔精选必看研判") -> List[Dict[str, Any]]:
    """将小兔精选包裹在原生折叠面板内，若条数过多自动切分。"""
    if not curated:
        return []
    chunk_size = 8
    panels = []
    for c_idx in range(0, len(curated), chunk_size):
        chunk = curated[c_idx:c_idx + chunk_size]
        inner_elements = []
        for idx, item in enumerate(chunk):
            inner_elements.append({
                "tag": "markdown",
                "content": format_repo_line(item)
            })
            if idx < len(chunk) - 1:
                inner_elements.append({"tag": "hr"})
                
        suffix = f" ({c_idx+1}~{c_idx+len(chunk)})" if len(curated) > chunk_size else f"（共 {len(curated)} 个项目）"
        panels.append({
            "tag": "collapsible_panel",
            "expanded": False,
            "header": {
                "title": {"tag": "plain_text", "content": f"{title_prefix}{suffix} · 点击展开"}
            },
            "border": {"color": "orange", "corner_radius": "6px"},
            "elements": inner_elements
        })
    return panels

def build_feishu_cards(
    day: str,
    summary: Dict[str, Any],
    curated: List[Dict[str, Any]],
    raw_boards: Dict[str, List[str]],
    notes: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """装配飞书卡片列表，超过 CARD_BYTE_LIMIT 自动细粒度拆页。"""
    
    # 1. 顶部概览
    fetched_at = summary.get("fetched_at", "")[:16].replace("T", " ")
    total = summary.get("total_repos", 0)
    counts = summary.get("counts", {})
    must_c = counts.get("must", 0)
    rec_c = counts.get("rec", 0)
    watch_c = counts.get("watch", 0)
    rej_c = counts.get("rejected", 0)
    
    header_element = {
        "tag": "markdown",
        "content": (
            f"【抓取时间】{fetched_at}（北京时间）· 五榜共 {total} 个去重仓库\n"
            f"【研判结论】**🔥 必看 {must_c} 个** · **✨ 推荐 {rec_c} 个** · **📌 关注 {watch_c} 个** · **⚠️ 一票否决 {rej_c} 个**\n"
            f"<font color='grey'>已严格收敛精选区（仅保留必看深度研判），下方各榜单均升级为双列表格展示。</font>"
        )
    }
    
    # 2. 精选必看列表
    curated_panels = build_curated_panel(curated)
        
    # 3. 原始榜单抽屉列表 (双列表格形态: 项目名 + 核心功能说明)
    board_titles = {
        "daily": "日榜原文（今日 UTC）",
        "weekly": "周榜原文",
        "monthly": "月榜原文",
        "yearly": "年榜原文",
        "github_trending": "GitHub Trending 历史原文"
    }
    raw_panels = []
    for k in ["daily", "weekly", "monthly", "yearly", "github_trending"]:
        if k in raw_boards:
            raw_panels.extend(build_collapsible_table_panel(board_titles[k], raw_boards[k], notes=notes))
            
    all_elements = [header_element] + curated_panels + raw_panels
    
    # 4. 拆页封包计算
    WRAPPER_OVERHEAD = 1000
    PAGE_TARGET_LIMIT = CARD_BYTE_LIMIT - WRAPPER_OVERHEAD
    
    pages: List[List[Dict[str, Any]]] = []
    cur_page: List[Dict[str, Any]] = []
    
    for el in all_elements:
        candidate = cur_page + [el]
        candidate_bytes = len(json.dumps(candidate, ensure_ascii=False).encode("utf-8"))
        if cur_page and candidate_bytes > PAGE_TARGET_LIMIT:
            pages.append(cur_page)
            cur_page = [el]
        else:
            cur_page = candidate
            
    if cur_page:
        pages.append(cur_page)
        
    cards: List[Dict[str, Any]] = []
    total_pages = len(pages)
    
    for idx, els in enumerate(pages, 1):
        page_suffix = f" ({idx}/{total_pages})" if total_pages > 1 else ""
        title = f"Trendshift 日报 · {day}{page_suffix}"
        
        cards.append({
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": "orange"
            },
            "elements": els
        })
        
    return cards
