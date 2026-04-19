"""Mine labels.jsonl for proposed rules.yaml additions."""
from __future__ import annotations

import re
from collections import defaultdict
from email.utils import parseaddr

_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "by", "for",
        "from", "fwd", "has", "have", "in", "is", "it", "its", "new",
        "not", "of", "on", "or", "pr", "re", "repo", "s", "that", "the",
        "this", "to", "was", "were", "will", "with", "you", "your",
    }
)


def sender_domain(address: str) -> str:
    _, addr = parseaddr(address or "")
    if "@" not in addr:
        return ""
    return "@" + addr.split("@", 1)[1].lower().strip(">")


def subject_tokens(subject: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-zA-Z]{3,}", (subject or "").lower())
        if t not in _STOPWORDS
    ]


def suggest_additions(labels: list[dict], min_occurrences: int = 3) -> dict:
    """Derive proposed rule additions from labelled messages.

    A sender domain with mean rating <=2 over min_occurrences+ labels is a
    spam_senders candidate; mean >=4 is a high_priority_senders candidate.
    Subject tokens seen only in low-rated mail become spam_keywords; tokens
    only in high-rated mail become high_keywords.
    """
    by_domain: dict[str, list[int]] = defaultdict(list)
    low_tokens: dict[str, int] = defaultdict(int)
    high_tokens: dict[str, int] = defaultdict(int)

    for lbl in labels:
        stars = lbl.get("stars")
        if not isinstance(stars, int):
            continue
        dom = sender_domain(lbl.get("from", ""))
        if dom:
            by_domain[dom].append(stars)
        tokens = set(subject_tokens(lbl.get("subject", "")))
        if stars <= 2:
            for t in tokens:
                low_tokens[t] += 1
        elif stars >= 4:
            for t in tokens:
                high_tokens[t] += 1

    spam_senders = sorted(
        d for d, rs in by_domain.items()
        if len(rs) >= min_occurrences and sum(rs) / len(rs) <= 2.0
    )
    high_senders = sorted(
        d for d, rs in by_domain.items()
        if len(rs) >= min_occurrences and sum(rs) / len(rs) >= 4.0
    )
    spam_keywords = sorted(
        t for t, c in low_tokens.items()
        if c >= min_occurrences and high_tokens.get(t, 0) == 0
    )
    high_keywords = sorted(
        t for t, c in high_tokens.items()
        if c >= min_occurrences and low_tokens.get(t, 0) == 0
    )
    return {
        "high_priority_senders": high_senders,
        "high_keywords": high_keywords,
        "spam_senders": spam_senders,
        "spam_keywords": spam_keywords,
    }
