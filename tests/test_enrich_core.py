from datetime import date
from trendshift_daily.enrich import hard_stale_verdict, parse_repo_meta


def test_archived_is_hard_rejected():
    v = hard_stale_verdict({"archived": True, "pushed_at": "2026-10-01"}, today=date(2026, 10, 9))
    assert v == ("不推荐", "已归档")


def test_two_years_stale_is_hard_rejected():
    v = hard_stale_verdict({"archived": False, "pushed_at": "2024-01-01"}, today=date(2026, 10, 9))
    assert v == ("不推荐", "两年以上未更新")


def test_missing_pushed_at_never_triggers():
    # 防误杀:数据缺失不得触发否决
    assert hard_stale_verdict({"archived": False, "pushed_at": None}, today=date(2026, 10, 9)) is None


def test_fresh_repo_not_rejected():
    assert hard_stale_verdict({"archived": False, "pushed_at": "2026-09-30"}, today=date(2026, 10, 9)) is None


def test_parse_repo_meta_extracts_fields_and_drops_extras():
    raw = {"description": "d", "language": "Go", "stargazers_count": 5, "topics": ["x"],
           "pushed_at": "2026-10-08T01:02:03Z", "archived": False, "html_url": "u", "owner": {"login": "z"}}
    m = parse_repo_meta(raw)
    assert m == {"description": "d", "language": "Go", "stars": 5, "topics": ["x"],
                 "pushed_at": "2026-10-08", "archived": False, "html_url": "u"}
