"""
Sentiment + emotion classifier for AR/EN mentions.

In production this would call:
  - Anthropic Claude (best AR/EN nuance, ~$0.001/mention)
  - or AWS Comprehend (cheap, supports AR)
  - or a fine-tuned XLM-RoBERTa hosted on SageMaker

This file ships with a lightweight lexicon-based fallback so the service
runs without API keys for local dev. Swap `_lexicon_score` for an LLM call
in production via the SENTIMENT_BACKEND env var.
"""
from __future__ import annotations
import os
import re
from typing import Optional

from models import Mention, Sentiment, Emotion, ServiceMatch


# --- RTA-specific keyword taxonomy ---------------------------------------

SERVICE_KEYWORDS: dict[ServiceMatch, list[str]] = {
    ServiceMatch.BUS:    ["bus", "rta bus", "feeder", "حافلة", "باص"],
    ServiceMatch.TAXI:   ["taxi", "hala", "careem", "uber", "dtc",
                          "تاكسي", "هلا", "أجرة"],
    ServiceMatch.MARINE: ["abra", "ferry", "water taxi", "marine",
                          "عبرة", "بحري", "تاكسي مائي"],
    ServiceMatch.NOL:    ["nol card", "nol", "نول", "بطاقة نول"],
    ServiceMatch.METRO:  ["metro", "rta metro", "مترو"],
}

# Lightweight bilingual sentiment lexicon — production replaces with LLM.
# Words are normalized lowercase; Arabic forms intentionally simple (no diacritics).
NEGATIVE_TERMS = {
    "en": ["delay", "delayed", "late", "broken", "rude", "refused", "refuse", "cancelled",
           "dirty", "filthy", "unsafe", "dangerous", "overcharged", "scam", "ignored",
           "terrible", "horrible", "worst", "awful", "disgusted", "frustrated",
           "complaint", "useless", "waiting", "stuck", "no show"],
    "ar": ["تأخير", "متأخر", "وسخ", "خطر", "مرفوض", "رفض", "سيء", "أسوأ",
           "غضب", "زبالة", "غش", "احتيال", "شكوى", "انتظار"],
}

POSITIVE_TERMS = {
    "en": ["thanks", "thank you", "great", "amazing", "excellent", "fast", "clean",
           "polite", "helpful", "smooth", "comfortable", "love", "appreciate",
           "professional", "kind", "perfect"],
    "ar": ["شكرا", "ممتاز", "رائع", "نظيف", "محترم", "مريح", "أحب",
           "أفضل", "تقدير", "كفؤ"],
}

EMOTION_PATTERNS: dict[Emotion, list[str]] = {
    Emotion.FRUSTRATION:           ["furious", "angry", "fed up", "غاضب", "فاشل"],
    Emotion.URGENCY:               ["urgent", "asap", "now", "immediately", "عاجل", "فوراً"],
    Emotion.SAFETY_CONCERN:        ["unsafe", "dangerous", "accident", "crash", "خطر", "حادث"],
    Emotion.APPRECIATION:          ["thanks", "thank", "amazing", "love", "شكرا"],
    Emotion.CONFUSION:             ["confused", "don't understand", "unclear", "محتار", "مش فاهم"],
    Emotion.ACCESSIBILITY_CONCERN: ["wheelchair", "accessibility", "disabled", "ramp", "إعاقة", "كرسي متحرك"],
    Emotion.FAIRNESS_CONCERN:      ["unfair", "discrimination", "biased", "ظلم", "تمييز"],
}


# --- Detection helpers ---------------------------------------------------

def detect_language(text: str) -> str:
    """Crude detection: any Arabic codepoint → 'ar', else 'en'."""
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"


def detect_service(text: str) -> tuple[ServiceMatch, list[str]]:
    """Returns (service, matched_keywords). Picks the service with most hits."""
    lo = text.lower()
    best = ServiceMatch.UNKNOWN
    best_count = 0
    matched: list[str] = []
    for svc, kws in SERVICE_KEYWORDS.items():
        hits = [k for k in kws if k in lo]
        if len(hits) > best_count:
            best, best_count, matched = svc, len(hits), hits
    if best == ServiceMatch.UNKNOWN and any(k in lo for k in ["rta", "dubai transport", "هيئة الطرق"]):
        best = ServiceMatch.GENERAL
    return best, matched


def detect_emotions(text: str) -> list[Emotion]:
    lo = text.lower()
    return [e for e, terms in EMOTION_PATTERNS.items() if any(t in lo for t in terms)]


def _lexicon_score(text: str, lang: str) -> tuple[float, float]:
    """Returns (score, confidence) using a very simple lexicon."""
    lo = text.lower()
    pos = sum(1 for w in POSITIVE_TERMS.get(lang, []) if w in lo)
    neg = sum(1 for w in NEGATIVE_TERMS.get(lang, []) if w in lo)
    if pos == 0 and neg == 0:
        return 0.0, 0.3
    score = (pos - neg) / max(pos + neg, 1)
    confidence = min(0.5 + 0.15 * (pos + neg), 0.85)
    return float(score), float(confidence)


async def _llm_score(text: str, lang: str) -> tuple[float, float]:
    """
    Production path: call Claude with a structured prompt.

    Skeleton — the live integration would use the Anthropic SDK with
    a JSON-mode prompt. We don't ship live keys here.
    """
    # from anthropic import AsyncAnthropic
    # client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # resp = await client.messages.create(
    #     model="claude-haiku-4-5-20251001",
    #     max_tokens=80,
    #     messages=[{"role": "user", "content": (
    #         "Score the sentiment of this customer-feedback post about a public "
    #         "transport service. Reply ONLY as JSON: "
    #         '{"score": float in [-1,1], "confidence": float in [0,1]}.\n\n'
    #         f"Post ({lang}): {text}"
    #     )}],
    # )
    # data = json.loads(resp.content[0].text)
    # return float(data["score"]), float(data["confidence"])
    raise NotImplementedError("Wire the Anthropic call before enabling LLM backend.")


# --- Priority scoring ----------------------------------------------------

def compute_priority(m: Mention) -> float:
    """
    0–100 score combining sentiment, reach, and risk signals.
    Mirrors the priority logic described in the PTCHP doc § 10.10.
    """
    s = 0.0
    # Negative sentiment intensity → up to 40 pts
    if m.sentiment == Sentiment.NEGATIVE:
        s += 40 * abs(m.sentiment_score)
    elif m.sentiment == Sentiment.NEUTRAL:
        s += 10
    # Reach (log-scaled) → up to 25 pts
    import math
    if m.reach_estimate > 0:
        s += min(25, 4 * math.log10(max(m.reach_estimate, 10)))
    # Engagement → up to 15 pts
    eng = m.likes + m.shares * 2 + m.replies
    if eng > 0:
        s += min(15, 3 * math.log10(max(eng, 1)))
    # Risk emotions → up to 20 pts
    risk = {Emotion.SAFETY_CONCERN, Emotion.ACCESSIBILITY_CONCERN, Emotion.URGENCY}
    s += 20 if any(e in risk for e in m.emotions) else 0
    return round(min(s, 100.0), 1)


# --- Public API ----------------------------------------------------------

async def enrich(m: Mention) -> Mention:
    """Fill sentiment, emotions, service match, priority. Mutates and returns."""
    backend = os.environ.get("SENTIMENT_BACKEND", "lexicon")

    m.language = detect_language(m.text)
    m.service_match, m.matched_keywords = detect_service(m.text)
    m.emotions = detect_emotions(m.text)

    if backend == "llm":
        score, conf = await _llm_score(m.text, m.language)
    else:
        score, conf = _lexicon_score(m.text, m.language)

    m.sentiment_score = score
    m.confidence = conf
    if score <= -0.2:
        m.sentiment = Sentiment.NEGATIVE
    elif score >= 0.2:
        m.sentiment = Sentiment.POSITIVE
    else:
        m.sentiment = Sentiment.NEUTRAL

    m.priority_score = compute_priority(m)
    return m
