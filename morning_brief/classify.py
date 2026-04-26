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


def _first_match(patterns: Iterable[str], text: str) -> str | None:
    text_lc = text.lower()
    for p in patterns:
        if p.lower() in text_lc:
            return p
    return None


def classify_with_reason(
    sender: str, subject: str, rules: Rules
) -> tuple[str, str]:
    """Return (bucket, reason). Reason is a short ``rule_kind:matched_value``."""
    hit = _first_match(rules.spam_senders, sender)
    if hit:
        return "SPAM", f"spam_sender:{hit}"
    hit = _first_match(rules.spam_keywords, subject)
    if hit:
        return "SPAM", f"spam_keyword:{hit}"
    hit = _first_match(rules.high_priority_senders, sender)
    if hit:
        return "HIGH", f"high_sender:{hit}"
    hit = _first_match(rules.high_keywords, subject)
    if hit:
        return "HIGH", f"high_keyword:{hit}"
    if rules.github_sender and rules.github_sender in sender.lower():
        hit = _first_match(rules.github_low_keywords, subject)
        if hit:
            return "LOW", f"github_low_keyword:{hit}"
        return "MEDIUM", f"github_sender:{rules.github_sender}"
    return "MEDIUM", "default"


def classify(sender: str, subject: str, rules: Rules) -> str:
    bucket, _ = classify_with_reason(sender, subject, rules)
    return bucket
