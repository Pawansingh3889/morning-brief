"""Unit tests for the rule-based classifier."""
from morning_brief.classify import Rules, classify, classify_with_reason

RULES = Rules.from_dict(
    {
        "high_priority_senders": ["@canonical.com"],
        "high_keywords": ["review requested", "ci failed"],
        "github_sender": "notifications@github.com",
        "github_low_keywords": ["starred", "released"],
        "spam_senders": ["@myexpertify.org"],
        "spam_keywords": ["reaching out to connect"],
    }
)


def test_spam_sender_match():
    assert classify("Abigail <a@myexpertify.org>", "Hi", RULES) == "SPAM"


def test_spam_keyword_match():
    assert classify("random@example.com", "Reaching out to connect", RULES) == "SPAM"


def test_high_priority_sender():
    assert classify("hr@canonical.com", "Interview next week", RULES) == "HIGH"


def test_high_keyword_wins_over_github_sender():
    # A review-requested email from GitHub is HIGH, not MEDIUM.
    assert (
        classify("notifications@github.com", "Review requested on PR #1", RULES)
        == "HIGH"
    )


def test_github_low_keyword():
    assert (
        classify("notifications@github.com", "user starred your repo", RULES) == "LOW"
    )


def test_github_default_medium():
    assert (
        classify("notifications@github.com", "[repo] New comment on PR #2", RULES)
        == "MEDIUM"
    )


def test_unknown_defaults_medium():
    assert classify("someone@example.com", "Random subject", RULES) == "MEDIUM"


def test_spam_beats_high():
    # SPAM is checked first, so a spam-list sender wins even with a high subject.
    assert (
        classify("a@myexpertify.org", "Review requested urgently", RULES) == "SPAM"
    )


def test_case_insensitive():
    assert classify("HR@Canonical.com", "INTERVIEW", RULES) == "HIGH"


def test_empty_rules_defaults_medium():
    rules = Rules.from_dict({})
    assert classify("anyone@example.com", "anything", rules) == "MEDIUM"


def test_reason_spam_sender_includes_pattern():
    bucket, reason = classify_with_reason("a@myexpertify.org", "Hi", RULES)
    assert bucket == "SPAM"
    assert reason == "spam_sender:@myexpertify.org"


def test_reason_high_keyword_includes_pattern():
    bucket, reason = classify_with_reason(
        "anyone@example.com", "Review requested please", RULES
    )
    assert bucket == "HIGH"
    assert reason == "high_keyword:review requested"


def test_reason_github_default_medium():
    bucket, reason = classify_with_reason(
        "notifications@github.com", "PR comment", RULES
    )
    assert bucket == "MEDIUM"
    assert reason.startswith("github_sender:")


def test_reason_github_low_keyword():
    bucket, reason = classify_with_reason(
        "notifications@github.com", "user starred your repo", RULES
    )
    assert bucket == "LOW"
    assert reason == "github_low_keyword:starred"


def test_reason_default():
    _, reason = classify_with_reason("x@y.com", "anything", RULES)
    assert reason == "default"
