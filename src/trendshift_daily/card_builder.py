"""Trendshift 日报 · 飞书交互卡片渲染器。
实现 F10(卡片渲染与拆页)。附带直接跳转链接、专业中文描述、专属设计感徽章、折叠面板与优雅拆页。
"""
import json
from typing import Dict, Any, List

CARD_BYTE_LIMIT = 25000  # 飞书单卡 JSON 保守上限

def format_repo_line(item: Dict[str, Any]) -> str:
    """按规范渲染单个仓库的卡片正文 (高阶设计感标签 + GitHub 超链接 + 全角标点 + 严谨依凭)。"""
    repo = item["repo"]
    url = item.get("url") or f"https://github.com/{repo}"
    tag = item.get("tag", "关注")
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

def build_collapsible_panel(title: str, items: List[str]) -> Dict[str, Any]:
    """构建飞书原生折叠面板 (默认收起，每个条目附带 GitHub 直跳链接)。"""
    formatted_lines = []
    for i, s in enumerate(items, 1):
        repo_name = s.split()[0]
        extra = s[len(repo_name):].strip()
        extra_str = f" {extra}" if extra else ""
        link_str = f"[{repo_name}](https://github.com/{repo_name}){extra_str}"
        formatted_lines.append(f"{i}. {link_str}")
        
    lines = "\n".join(formatted_lines) or "（本榜无数据）"
    return {
        "tag": "collapsible_panel",
        "expanded": False,
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"{title}（{len(items)} 条）"
            }
        },
        "border": {
            "color": "orange",
            "corner_radius": "6px"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": lines
            }
        ]
    }

def build_feishu_cards(
    day: str,
    summary: Dict[str, Any],
    curated: List[Dict[str, Any]],
    raw_boards: Dict[str, List[str]]
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
            f"【研判结论】**🔥 必看 {must_c} 个** · **✨ 推荐 {rec_c} 个** · **📌 关注 {watch_c} 个** · **⚠️ 一票否决 {rej_c} 个**"
        )
    }
    
    # 2. 精选列表
    curated_elements = []
    if curated:
        curated_elements.append({
            "tag": "markdown",
            "content": "**🌟 小兔精选（点击仓库名直达 GitHub · 深度研判）**"
        })
        for idx, item in enumerate(curated):
            curated_elements.append({
                "tag": "markdown",
                "content": format_repo_line(item)
            })
            if idx < len(curated) - 1:
                curated_elements.append({
                    "tag": "hr"
                })
        
    # 3. 折叠面板列表
    board_titles = {
        "daily": "日榜原文（今日 UTC）",
        "weekly": "周榜原文",
        "monthly": "月榜原文",
        "yearly": "年榜原文",
        "github_trending": "GitHub Trending 历史原文"
    }
    panels = []
    for k in ["daily", "weekly", "monthly", "yearly", "github_trending"]:
        if k in raw_boards:
            panels.append(build_collapsible_panel(board_titles[k], raw_boards[k]))
            
    all_elements = [header_element] + curated_elements + panels
    
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
