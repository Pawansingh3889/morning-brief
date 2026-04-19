"""Rule-based classifier for inbox messages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

BUCKETS = ("HIGH", "MEDIUM", "LOW", "SPAM")


@dataclass(frozen=True)
class Rules:
    high_priority_senders: tuple[str, ...]
    high_keywords: tuple[str, ...]
    github_sender: str
    github_low_keywords: tuple[str, ...]
    spam_senders: tuple[str, ...]
    spam_keywords: tuple[str, ...]

    @classmethod
    def from_dict(cls, d: dict) -> "Rules":
        def _tuple(key: str) -> tuple[str, ...]:
            return tuple(d.get(key) or [])

        return cls(
            high_priority_senders=_tuple("high_priority_senders"),
            high_keywords=_tuple("high_keywords"),
            github_sender=(d.get("github_sender") or "").lower(),
            github_low_keywords=_tuple("github_low_keywords"),
            spam_senders=_tuple("spam_senders"),
            spam_keywords=_tuple("spam_keywords"),
        )


def _any_contains(patterns: Iterable[str], text: str) -> bool:
    text_lc = text.lower()
    return any(p.lower() in text_lc for p in patterns)


def classify(sender: str, subject: str, rules: Rules) -> str:
    if _any_contains(rules.spam_senders, sender):
        return "SPAM"
    if _any_contains(rules.spam_keywords, subject):
        return "SPAM"
    if _any_contains(rules.high_priority_senders, sender):
        return "HIGH"
    if _any_contains(rules.high_keywords, subject):
        return "HIGH"
    if rules.github_sender and rules.github_sender in sender.lower():
        if _any_contains(rules.github_low_keywords, subject):
            return "LOW"
        return "MEDIUM"
    return "MEDIUM"
