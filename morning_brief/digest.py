"""Markdown digest rendering."""
from __future__ import annotations

from email.utils import parseaddr

from morning_brief.classify import BUCKETS


def render(items: dict, date_iso: str, labels: dict | None = None) -> str:
    """Render the markdown digest.

    If ``labels`` covers at least one item, group by 5..1 stars (with an
    Unrated section for anything not yet labelled). Otherwise fall back to
    the rule-based bucket output.
    """
    if labels and any(k in labels for k in items):
        return _render_by_stars(items, date_iso, labels)
    return _render_by_bucket(items, date_iso)


def _display_sender(raw: str) -> str:
    name, addr = parseaddr(raw)
    return name or addr or "(unknown)"


def _render_by_bucket(items: dict, date_iso: str) -> str:
    by_bucket: dict[str, list[dict]] = {b: [] for b in BUCKETS}
    for item in items.values():
        by_bucket[item["bucket"]].append(item)

    total = sum(len(v) for v in by_bucket.values())
    lines = [f"# Morning brief {date_iso}", f"_{total} messages classified_", ""]
    for bucket in BUCKETS:
        entries = by_bucket[bucket]
        if not entries:
            continue
        lines.append(f"## {bucket} ({len(entries)})")
        for item in entries:
            lines.append(f"- **{_display_sender(item['from'])}** {item['subject']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _render_by_stars(items: dict, date_iso: str, labels: dict) -> str:
    by_stars: dict[int, list[dict]] = {}
    unrated: list[dict] = []
    for msg_id, item in items.items():
        stars = labels.get(msg_id, {}).get("stars")
        if isinstance(stars, int) and 1 <= stars <= 5:
            by_stars.setdefault(stars, []).append(item)
        else:
            unrated.append(item)

    total = len(items)
    lines = [f"# Morning brief {date_iso}", f"_{total} messages_", ""]
    for stars in (5, 4, 3, 2, 1):
        entries = by_stars.get(stars, [])
        if not entries:
            continue
        header = "\u2605" * stars
        lines.append(f"## {header} ({len(entries)})")
        for item in entries:
            lines.append(f"- **{_display_sender(item['from'])}** {item['subject']}")
        lines.append("")
    if unrated:
        lines.append(f"## Unrated ({len(unrated)})")
        for item in unrated:
            lines.append(f"- **{_display_sender(item['from'])}** {item['subject']}")
        lines.append("")
    return "\n".join(lines) + "\n"
