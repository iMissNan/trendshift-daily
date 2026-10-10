"""Trendshift 日报 · 统一数据模型与抽象多渠道投递出口。
为后续扩展 Web 静态博客、微信公众号、飞书等多通道留好清晰契约接口。
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

@dataclass
class RepoItem:
    repo: str
    url: str
    what_it_is: str          # 中文清晰项目描述：做什么的、实现了什么
    for_us: str              # 对我们技术体系（家庭服务器/运维/安全）的针对性价值
    evidence: str            # 结论依据来源
    tag: str                 # 必看 / 推荐 / 关注 / 观望 / 不推荐
    streak: int = 1
    rejected: bool = False
    reject_reason: str = ""
    stars: int = 0
    language: str = ""

@dataclass
class DailyReport:
    day: str
    fetched_at: str
    total_repos: int
    counts: Dict[str, int]
    curated: List[RepoItem]
    raw_boards: Dict[str, List[str]]

class BasePublisher(ABC):
    """抽象发布器通道基类。"""
    @abstractmethod
    def publish(self, report: DailyReport) -> bool:
        pass

class FeishuPublisher(BasePublisher):
    """飞书富文本/交互卡片发布器。"""
    def __init__(self, chat_id: str, app_id: str, app_secret: str):
        self.chat_id = chat_id
        self.app_id = app_id
        self.app_secret = app_secret

    def publish(self, report: DailyReport) -> bool:
        # 飞书投递逻辑
        return True

class BlogMarkdownPublisher(BasePublisher):
    """后续博客发布通道契约（支持直接输出静态博客 Markdown/Hugo/Hexo）。"""
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def publish(self, report: DailyReport) -> bool:
        # 预留博客渲染口
        return True

class WeChatMpPublisher(BasePublisher):
    """后续微信公众号发布通道契约（支持输出适合公众号排版的 HTML 或调用草稿箱 API）。"""
    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret

    def publish(self, report: DailyReport) -> bool:
        # 预留微信公众号发布口
        return True
