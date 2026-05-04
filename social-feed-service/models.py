"""Unified data model for social mentions across all platforms."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Platform(str, Enum):
    X = "x"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    REDDIT = "reddit"
    NEWS_RSS = "news_rss"
    YOUTUBE = "youtube"  # adapter not yet implemented


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Emotion(str, Enum):
    FRUSTRATION = "frustration"
    URGENCY = "urgency"
    SAFETY_CONCERN = "safety_concern"
    APPRECIATION = "appreciation"
    CONFUSION = "confusion"
    ACCESSIBILITY_CONCERN = "accessibility_concern"
    FAIRNESS_CONCERN = "fairness_concern"


class ServiceMatch(str, Enum):
    """Which RTA service line the mention is about, if detectable."""
    BUS = "bus"
    TAXI = "taxi"
    MARINE = "marine"
    NOL = "nol"
    METRO = "metro"
    GENERAL = "general"
    UNKNOWN = "unknown"


class Mention(BaseModel):
    """Unified shape for a social-media mention, normalized across platforms."""

    # Identity
    id: str = Field(..., description="Stable cross-platform ID: '{platform}:{native_id}'")
    platform: Platform
    native_id: str = Field(..., description="Platform-native post ID")
    url: Optional[str] = None

    # Author (anonymized for privacy — only public handle, never PII)
    author_handle: Optional[str] = None
    author_followers: Optional[int] = None
    author_verified: bool = False

    # Content
    text: str
    language: str = Field("en", description="ISO 639-1 — typically 'en' or 'ar'")
    created_at: datetime
    fetched_at: datetime

    # Engagement (used for priority scoring — public reach matters)
    likes: int = 0
    shares: int = 0  # retweets / shares / boosts
    replies: int = 0
    reach_estimate: int = 0  # author_followers proxy

    # AI enrichment (filled by sentiment.py)
    sentiment: Sentiment = Sentiment.NEUTRAL
    sentiment_score: float = Field(0.0, ge=-1.0, le=1.0)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    emotions: list[Emotion] = Field(default_factory=list)
    service_match: ServiceMatch = ServiceMatch.UNKNOWN
    matched_keywords: list[str] = Field(default_factory=list)

    # Operational priority (higher = more urgent for ops review)
    priority_score: float = Field(0.0, ge=0.0, le=100.0)

    def to_dashboard_dict(self) -> dict:
        """Trimmed shape sent to the dashboard — author handles partly masked."""
        return {
            "id": self.id,
            "platform": self.platform.value,
            "url": self.url,
            "handle": self._mask_handle(),
            "verified": self.author_verified,
            "reach": self.reach_estimate,
            "text": self.text,
            "language": self.language,
            "createdAt": self.created_at.isoformat(),
            "sentiment": self.sentiment.value,
            "sentimentScore": round(self.sentiment_score, 2),
            "emotions": [e.value for e in self.emotions],
            "service": self.service_match.value,
            "priority": round(self.priority_score, 1),
            "engagement": {"likes": self.likes, "shares": self.shares, "replies": self.replies},
        }

    def _mask_handle(self) -> Optional[str]:
        if not self.author_handle:
            return None
        h = self.author_handle.lstrip("@")
        if len(h) <= 3:
            return "@" + h[0] + "•••"
        return "@" + h[:2] + "•••" + h[-1]


class MentionStats(BaseModel):
    """Aggregate stats for the dashboard's stats panel."""
    total: int
    window_minutes: int
    by_platform: dict[str, int]
    by_sentiment: dict[str, int]
    by_service: dict[str, int]
    avg_sentiment: float
    spike_alert: bool = False
    spike_reason: Optional[str] = None
    peak_keyword: Optional[str] = None
    last_updated: datetime
