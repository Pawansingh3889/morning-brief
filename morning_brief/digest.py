"""Markdown digest rendering."""
from __future__ import annotations

from email.utils import parseaddr

from morning_brief.classify import BUCKETS


def render(
    items: dict,
    date_iso: str,
    labels: dict | None = None,
    collapse_threads: bool = True,
) -> str:
    """Render the markdown digest.

    If ``labels`` covers at least one item, group by 5..1 stars (with an
    Unrated section for anything not yet labelled). Otherwise fall back to
    the rule-based bucket output. When ``collapse_threads`` is True, messages
    sharing a Gmail ``thread_id`` collapse to a single entry annotated with
    the thread size.
    """
    working_items = _collapse_threads(items) if collapse_threads else items
    if labels and any(k in labels for k in working_items):
        return _render_by_stars(working_items, date_iso, labels)
    return _render_by_bucket(working_items, date_iso)


def _collapse_threads(items: dict) -> dict:
    """Collapse items sharing a thread_id. Items missing thread_id pass through."""
    by_thread: dict[str, list[tuple[str, dict]]] = {}
    out: dict = {}
    for mid, item in items.items():
        tid = item.get("thread_id")
        if not tid:
            out[mid] = item
            continue
        by_thread.setdefault(tid, []).append((mid, item))
    for tid, members in by_thread.items():
        members.sort(key=lambda x: x[1].get("date", ""))
        rep_mid, rep_item = members[0]
        rep = dict(rep_item)
        rep["thread_count"] = len(members)
        out[rep_mid] = rep
    return out


def _display_sender(raw: str) -> str:
    name, addr = parseaddr(raw)
    return name or addr or "(unknown)"


def _format_entry(item: dict) -> str:
    base = f"- **{_display_sender(item['from'])}** {item['subject']}"
    count = item.get("thread_count", 1)
    if count > 1:
        base += f" _({count} msgs)_"
    return base


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
            lines.append(_format_entry(item))
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
            lines.append(_format_entry(item))
        lines.append("")
    if unrated:
        lines.append(f"## Unrated ({len(unrated)})")
        for item in unrated:
            lines.append(_format_entry(item))
        lines.append("")
    return "\n".join(lines) + "\n"
