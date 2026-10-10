import pytest
import json
from trendshift_daily.card_builder import (
    build_feishu_cards,
    format_repo_line,
    CARD_BYTE_LIMIT
)

def test_build_feishu_cards_structure():
    day = "2026-10-10"
    summary = {
        "fetched_at": "2026-10-10T21:00:00+08:00",
        "total_repos": 93,
        "counts": {"must": 2, "rec": 5, "watch": 18, "rejected": 3}
    }
    curated = [
        {
            "repo": "NousResearch/hermes-agent",
            "tag": "必看",
            "streak": 4,
            "what_it_is": "开源原生常驻 AI Agent 架构",
            "for_us": "当前家庭服务器运行的正是此底座！新版本跟进直接关乎核心稳定性",
            "evidence": "GitHub Topics + README.md#Architecture",
            "rejected": False
        },
        {
            "repo": "old-legacy/abandoned-tool",
            "tag": "不推荐",
            "streak": 1,
            "what_it_is": "老旧工具",
            "for_us": "无用",
            "evidence": "GitHub API archived: true",
            "rejected": True,
            "reject_reason": "仓库已于 2024 年归档（Archived）且超 730 天无维护，触发一票否决"
        }
    ]
    raw_boards = {
        "daily": ["NousResearch/hermes-agent", "old-legacy/abandoned-tool"],
        "weekly": [],
        "monthly": [],
        "yearly": [],
        "github_trending": []
    }

    cards = build_feishu_cards(day=day, summary=summary, curated=curated, raw_boards=raw_boards)
    assert len(cards) >= 1
    card = cards[0]
    assert card["config"]["wide_screen_mode"] is True
    assert "Trendshift 日报" in card["header"]["title"]["content"]
    
    # 验证单卡字节数合规
    card_bytes = len(json.dumps(card, ensure_ascii=False).encode("utf-8"))
    assert card_bytes < CARD_BYTE_LIMIT

def test_card_builder_auto_pagination():
    day = "2026-10-10"
    summary = {
        "fetched_at": "2026-10-10T21:00:00+08:00",
        "total_repos": 100,
        "counts": {"must": 10, "rec": 20, "watch": 50, "rejected": 20}
    }
    # 构造大量数据触发自动拆页
    curated = []
    for i in range(40):
        curated.append({
            "repo": f"org/repo-{i}",
            "tag": "推荐",
            "streak": 1,
            "what_it_is": "这是一段很长很长的详细项目简介" * 15,
            "for_us": "这是一段针对家庭服务器业务价值的深度详细评估说明" * 10,
            "evidence": "README.md#Detailed-Docs",
            "rejected": False
        })
    raw_boards = {
        "daily": [f"org/repo-{i}" for i in range(50)],
        "weekly": [f"org/repo-{i}" for i in range(50)],
        "monthly": [],
        "yearly": [],
        "github_trending": []
    }

    cards = build_feishu_cards(day=day, summary=summary, curated=curated, raw_boards=raw_boards)
    assert len(cards) > 1  # 必然触发拆页
    for idx, card in enumerate(cards, 1):
        assert f"({idx}/{len(cards)})" in card["header"]["title"]["content"]
        card_bytes = len(json.dumps(card, ensure_ascii=False).encode("utf-8"))
        assert card_bytes < CARD_BYTE_LIMIT
