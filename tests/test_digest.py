"""Unit tests for digest rendering and thread collapse."""
from morning_brief.digest import _collapse_threads, render


def _msg(bucket: str, sender: str, subject: str, thread_id: str | None = None,
         date: str = "2026-04-26") -> dict:
    return {
        "from": sender,
        "subject": subject,
        "bucket": bucket,
        "thread_id": thread_id,
        "date": date,
    }


def test_collapse_groups_messages_sharing_thread_id():
    items = {
        "m1": _msg("HIGH", "a@x.com", "First", "t1", "2026-04-26"),
        "m2": _msg("HIGH", "a@x.com", "Re: First", "t1", "2026-04-26"),
        "m3": _msg("MEDIUM", "b@y.com", "Standalone", None),
    }
    out = _collapse_threads(items)
    assert len(out) == 2
    rep = next(v for v in out.values() if v.get("thread_count", 1) > 1)
    assert rep["thread_count"] == 2
    assert rep["subject"] == "First"  # earliest by date wins as the rep


def test_collapse_passes_through_when_no_thread_ids():
    items = {
        "m1": _msg("HIGH", "a@x.com", "Foo"),
        "m2": _msg("MEDIUM", "b@y.com", "Bar"),
    }
    out = _collapse_threads(items)
    assert out == items


def test_render_marks_thread_count_in_output():
    items = {
        "m1": _msg("HIGH", "a@x.com", "First", "t1", "2026-04-26"),
        "m2": _msg("HIGH", "a@x.com", "Re: First", "t1", "2026-04-26"),
    }
    md = render(items, "2026-04-26")
    assert "(2 msgs)" in md
    assert "## HIGH (1)" in md  # collapsed to one entry


def test_render_no_collapse_keeps_each_message():
    items = {
        "m1": _msg("HIGH", "a@x.com", "First", "t1", "2026-04-26"),
        "m2": _msg("HIGH", "a@x.com", "Re: First", "t1", "2026-04-26"),
    }
    md = render(items, "2026-04-26", collapse_threads=False)
    assert "## HIGH (2)" in md
    assert "(2 msgs)" not in md


def test_render_handles_legacy_state_without_thread_id():
    # v0.2.0 state.json has no thread_id field; render must still work.
    items = {
        "m1": {"from": "a@x.com", "subject": "Foo", "bucket": "HIGH"},
        "m2": {"from": "b@y.com", "subject": "Bar", "bucket": "MEDIUM"},
    }
    md = render(items, "2026-04-26")
    assert "## HIGH (1)" in md
    assert "## MEDIUM (1)" in md
