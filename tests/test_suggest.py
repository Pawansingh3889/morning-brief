"""Unit tests for suggest_additions pattern miner."""
from morning_brief.suggest import sender_domain, subject_tokens, suggest_additions


def test_sender_domain_extracts_domain():
    assert sender_domain("Abigail <a@myexpertify.org>") == "@myexpertify.org"
    assert sender_domain("bot@ads.co.uk") == "@ads.co.uk"


def test_sender_domain_empty_when_no_at():
    assert sender_domain("no-address") == ""


def test_subject_tokens_drops_stopwords_and_shorts():
    tokens = subject_tokens("Your new pull is ready for review")
    # "is", "the", "for" drop out as stopwords, "to"-style tokens dropped.
    assert "review" in tokens
    assert "ready" in tokens
    assert "is" not in tokens


def test_spam_sender_mean_below_two():
    labels = [
        {"msg_id": str(i), "from": "bot@ads.com", "subject": "offer", "stars": 1}
        for i in range(3)
    ]
    result = suggest_additions(labels)
    assert "@ads.com" in result["spam_senders"]
    assert "@ads.com" not in result["high_priority_senders"]


def test_high_priority_sender_mean_at_or_above_four():
    labels = [
        {
            "msg_id": str(i),
            "from": "hr@canonical.com",
            "subject": "interview",
            "stars": 5,
        }
        for i in range(3)
    ]
    result = suggest_additions(labels)
    assert "@canonical.com" in result["high_priority_senders"]


def test_below_min_occurrences_excluded():
    labels = [
        {"msg_id": "1", "from": "a@rare.com", "subject": "x", "stars": 1},
        {"msg_id": "2", "from": "a@rare.com", "subject": "x", "stars": 1},
    ]
    result = suggest_additions(labels, min_occurrences=3)
    assert "@rare.com" not in result["spam_senders"]


def test_keyword_exclusive_to_low_rated():
    labels = [
        {"msg_id": str(i), "from": f"a@{i}.com", "subject": "flash promo today", "stars": 1}
        for i in range(3)
    ]
    result = suggest_additions(labels)
    assert "flash" in result["spam_keywords"]
    assert "promo" in result["spam_keywords"]


def test_keyword_not_suggested_when_seen_in_high_rated():
    labels = [
        {"msg_id": str(i), "from": f"a@{i}.com", "subject": "urgent matter", "stars": 1}
        for i in range(3)
    ] + [
        {"msg_id": "99", "from": "a@good.com", "subject": "urgent update", "stars": 5}
    ]
    result = suggest_additions(labels)
    # "urgent" appears in both low and high, so should not be a spam keyword.
    assert "urgent" not in result["spam_keywords"]


def test_mid_rated_labels_do_not_vote():
    labels = [
        {"msg_id": str(i), "from": f"a@{i}.com", "subject": "weekly digest", "stars": 3}
        for i in range(5)
    ]
    result = suggest_additions(labels)
    # 3-star subjects should not push tokens into either keyword bucket.
    assert "weekly" not in result["spam_keywords"]
    assert "weekly" not in result["high_keywords"]
