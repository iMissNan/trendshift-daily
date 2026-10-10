import pytest
from trendshift_daily.pipeline import load_config, run_self_check, run_pipeline

def test_load_config():
    config = load_config("config/trendshift.yaml")
    assert "source" in config
    assert "github" in config
    assert "feishu" in config
    assert config["tagging"]["must_daily_cap"] == 3

def test_pipeline_dry_run():
    # 测试历史数据 2026-10-09 的回放 pipeline
    success = run_pipeline(
        config_path="config/trendshift.yaml",
        dry_run=True,
        target_day="2026-10-09"
    )
    assert success is True
