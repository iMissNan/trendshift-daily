import pytest
from datetime import datetime, timezone, timedelta
from trendshift_daily.analyzer import (
    determine_tag,
    is_hard_rejected,
    validate_analysis_result,
    build_analysis_prompt
)

def test_is_hard_rejected_archived():
    meta = {"archived": True, "pushed_at": "2026-10-01T00:00:00Z"}
    rejected, reason = is_hard_rejected(meta, stale_days=730)
    assert rejected is True
    assert "归档" in reason

def test_is_hard_rejected_stale():
    old_date = (datetime.now(timezone.utc) - timedelta(days=800)).isoformat()
    meta = {"archived": False, "pushed_at": old_date}
    rejected, reason = is_hard_rejected(meta, stale_days=730)
    assert rejected is True
    assert "超 730 天无维护" in reason

def test_is_hard_rejected_fresh():
    fresh_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    meta = {"archived": False, "pushed_at": fresh_date}
    rejected, reason = is_hard_rejected(meta, stale_days=730)
    assert rejected is False
    assert reason == ""

def test_determine_tag_priorities():
    # 硬否决
    meta_stale = {"archived": True, "pushed_at": "2024-01-01T00:00:00Z"}
    tag = determine_tag(meta_stale, analysis={"for_us": "没用"}, streak_days=5)
    assert tag == "不推荐"

    # 必看：强关联 + 新近更新
    fresh_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    meta_fresh = {"archived": False, "pushed_at": fresh_date, "stargazers_count": 5000}
    analysis_must = {
        "what_it_is": "Agent 底座",
        "for_us": "当前家庭服务器正在运行此系统",
        "evidence": "README.md#Architecture"
    }
    tag_must = determine_tag(meta_fresh, analysis_must, streak_days=4)
    assert tag_must == "必看"

def test_validate_analysis_result_strict_evidence():
    # 缺失依据应报错
    bad_data = {
        "what_it_is": "这是一个具备自动化代码生成与任务拆解的完整开源工具",
        "for_us": "对家庭服务器自动化运维很有用",
        "evidence": ""
    }
    valid, msg = validate_analysis_result(bad_data)
    assert valid is False
    assert "依据" in msg

    # 合法数据
    good_data = {
        "what_it_is": "这是一个具备自动化代码生成与任务拆解的完整开源工具",
        "for_us": "对家庭服务器自动化运维很有用",
        "evidence": "meta.description"
    }
    valid, msg = validate_analysis_result(good_data)
    assert valid is True
