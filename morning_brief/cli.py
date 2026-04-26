"""CLI entrypoint."""
from __future__ import annotations

import datetime as dt
from email.utils import parseaddr
from pathlib import Path

import typer
import yaml

from morning_brief import labels as labels_mod
from morning_brief import state as state_mod
from morning_brief import suggest as suggest_mod
from morning_brief.auth import gmail_service
from morning_brief.classify import Rules, classify, classify_with_reason
from morning_brief.digest import render
from morning_brief.notify import send as notify_send

app = typer.Typer(
    add_completion=False,
    help="Rule-based daily Gmail triage. Writes a markdown digest and notifies you.",
)


def _default_home() -> Path:
    return Path.home() / ".morning-brief"


def _header(message: dict, name: str) -> str:
    for h in message["payload"].get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _starter_rules() -> str:
    return """\
# morning-brief rules. Case-insensitive substring match.

high_priority_senders:
  - "@canonical.com"
  - "@posthog.com"

high_keywords:
  - "review requested"
  - "requested your review"
  - "mentioned you"
  - "assigned"
  - "merged your pull"
  - "ci failed"

github_sender: notifications@github.com

github_low_keywords:
  - "starred"
  - "subscribed you"
  - "released"
  - "new discussion"

spam_senders:
  - "@myexpertify.org"
  - "@myexpertify.com"

spam_keywords:
  - "reaching out to connect"
  - "freelance opportunity"
  - "i came across your profile"
"""


def _load_labels(home: Path) -> dict:
    return labels_mod.load_latest(home / "labels.jsonl")


@app.command()
def init(
    home: Path = typer.Option(None, help="Override data directory."),
) -> None:
    """Scaffold ~/.morning-brief/ with a starter rules.yaml."""
    home = home or _default_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "digests").mkdir(exist_ok=True)
    target = home / "rules.yaml"
    if target.exists():
        typer.echo(f"{target} already exists.")
        return
    target.write_text(_starter_rules())
    typer.echo(f"Wrote {target}")
    typer.echo(
        "Next:\n"
        f"  1. Drop credentials.json into {home}/ (Google Cloud OAuth, Desktop app).\n"
        "  2. Edit rules.yaml.\n"
        "  3. Run: morning-brief run"
    )


def _build_query(hours: int | None, days: int, unread_only: bool) -> str:
    """Compose the Gmail search query. ``hours`` wins over ``days`` when set."""
    window = f"newer_than:{hours}h" if hours is not None else f"newer_than:{days}d"
    parts = [window]
    if unread_only:
        parts.append("is:unread")
    return " ".join(parts)


@app.command()
def run(
    home: Path = typer.Option(None, help="Override data directory."),
    rules_path: Path = typer.Option(None, help="Path to rules.yaml."),
    days: int = typer.Option(1, help="Gmail newer_than window, in days."),
    hours: int = typer.Option(
        None,
        "--hours",
        "-H",
        help="Gmail newer_than window in hours. Overrides --days.",
    ),
    unread_only: bool = typer.Option(True, help="Limit to is:unread."),
    collapse_threads: bool = typer.Option(
        True,
        "--collapse-threads/--no-collapse-threads",
        help="Group messages sharing a Gmail thread into a single digest entry.",
    ),
    notify: bool = typer.Option(True, help="Show a desktop notification when done."),
) -> None:
    """Fetch recent mail, classify by rules, write today's digest."""
    home = home or _default_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "digests").mkdir(exist_ok=True)

    rules_file = rules_path or (home / "rules.yaml")
    if not rules_file.exists():
        typer.echo(
            f"rules.yaml not found at {rules_file}. Run 'morning-brief init' first.",
            err=True,
        )
        raise typer.Exit(1)
    rules = Rules.from_dict(yaml.safe_load(rules_file.read_text()) or {})

    state_path = home / "state.json"
    state = state_mod.prune(state_mod.load(state_path))

    creds_file = home / "credentials.json"
    token_file = home / "token.json"
    if not creds_file.exists():
        typer.echo(
            f"credentials.json not found at {creds_file}. See README for OAuth setup.",
            err=True,
        )
        raise typer.Exit(1)
    service = gmail_service(creds_file, token_file)

    query = _build_query(hours, days, unread_only)
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=200)
        .execute()
    )
    messages = result.get("messages", [])

    today = dt.date.today().isoformat()
    new = 0
    for m in messages:
        if m["id"] in state["processed"]:
            continue
        meta = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        sender = _header(meta, "From")
        subject = _header(meta, "Subject") or "(no subject)"
        bucket = classify(sender, subject, rules)
        state["processed"][m["id"]] = {
            "date": today,
            "from": sender,
            "subject": subject,
            "bucket": bucket,
            "thread_id": meta.get("threadId"),
        }
        new += 1

    state_mod.save(state, state_path)

    todays = {k: v for k, v in state["processed"].items() if v["date"] == today}
    labels_today = _load_labels(home)
    digest_path = home / "digests" / f"{today}.md"
    digest_path.write_text(
        render(todays, today, labels_today, collapse_threads=collapse_threads)
    )

    summary = f"{len(todays)} in digest, {new} new"
    typer.echo(f"Wrote {digest_path}: {summary}")
    if notify:
        notify_send(f"Morning brief {today}", summary)


@app.command()
def label(
    home: Path = typer.Option(None, help="Override data directory."),
    date: str = typer.Option(None, help="YYYY-MM-DD, defaults to today."),
) -> None:
    """Walk through unrated messages for a given date and rate each 1 to 5."""
    home = home or _default_home()
    date = date or dt.date.today().isoformat()

    state_path = home / "state.json"
    state = state_mod.load(state_path)
    todays = {k: v for k, v in state.get("processed", {}).items() if v["date"] == date}
    if not todays:
        typer.echo(
            f"No classified messages for {date}. Run 'morning-brief run' first."
        )
        raise typer.Exit(0)

    labels_path = home / "labels.jsonl"
    existing = labels_mod.load_latest(labels_path)
    to_label = [(mid, item) for mid, item in todays.items() if mid not in existing]
    if not to_label:
        typer.echo(f"All {len(todays)} messages for {date} already rated.")
        _refresh_digest(home, date)
        raise typer.Exit(0)

    typer.echo(
        f"Rating {len(to_label)} unrated messages for {date}."
        " Enter 1-5, 's' to skip, 'q' to save and quit."
    )
    for i, (mid, item) in enumerate(to_label, 1):
        name, addr = parseaddr(item["from"])
        display = name or addr or "(unknown)"
        typer.echo(f"\n[{i}/{len(to_label)}] {display}")
        typer.echo(f"    {item['subject']}")
        while True:
            ans = typer.prompt(
                "Stars (1-5, s, q)", default="s", show_default=False
            ).strip().lower()
            if ans == "q":
                typer.echo("Saved so far, quitting.")
                _refresh_digest(home, date)
                raise typer.Exit(0)
            if ans in ("s", ""):
                break
            if ans in {"1", "2", "3", "4", "5"}:
                labels_mod.append(
                    labels_path,
                    {
                        "msg_id": mid,
                        "date": item["date"],
                        "from": item["from"],
                        "subject": item["subject"],
                        "stars": int(ans),
                    },
                )
                break
            typer.echo("  Please enter 1-5, s, or q.")

    _refresh_digest(home, date)
    typer.echo(f"\nDone. Digest refreshed for {date}.")


def _refresh_digest(home: Path, date: str) -> None:
    state = state_mod.load(home / "state.json")
    todays = {k: v for k, v in state.get("processed", {}).items() if v["date"] == date}
    if not todays:
        return
    labels = _load_labels(home)
    (home / "digests").mkdir(exist_ok=True)
    (home / "digests" / f"{date}.md").write_text(render(todays, date, labels))


@app.command()
def preview(
    sender: str = typer.Option(..., "--sender", "-s", help="Sample 'Name <addr>' or bare email."),
    subject: str = typer.Option(..., "--subject", "-S", help="Sample subject line."),
    home: Path = typer.Option(None, help="Override data directory."),
    rules_path: Path = typer.Option(None, help="Path to rules.yaml."),
) -> None:
    """Test which bucket a hypothetical message would land in. No Gmail call."""
    home = home or _default_home()
    rules_file = rules_path or (home / "rules.yaml")
    if not rules_file.exists():
        typer.echo(f"rules.yaml not found at {rules_file}.", err=True)
        raise typer.Exit(1)
    rules = Rules.from_dict(yaml.safe_load(rules_file.read_text()) or {})
    bucket, reason = classify_with_reason(sender, subject, rules)
    typer.echo(f"Bucket: {bucket}")
    typer.echo(f"Reason: {reason}")


@app.command()
def why(
    msg_id: str = typer.Argument(..., help="Message ID stored in state.json."),
    home: Path = typer.Option(None, help="Override data directory."),
    rules_path: Path = typer.Option(None, help="Path to rules.yaml."),
) -> None:
    """Explain which rule classified a stored message. Useful after editing rules.yaml."""
    home = home or _default_home()
    state = state_mod.load(home / "state.json")
    item = state.get("processed", {}).get(msg_id)
    if not item:
        typer.echo(f"No record of '{msg_id}' in state.json.", err=True)
        raise typer.Exit(1)
    rules_file = rules_path or (home / "rules.yaml")
    if not rules_file.exists():
        typer.echo(f"rules.yaml not found at {rules_file}.", err=True)
        raise typer.Exit(1)
    rules = Rules.from_dict(yaml.safe_load(rules_file.read_text()) or {})
    bucket, reason = classify_with_reason(item["from"], item["subject"], rules)
    typer.echo(f"From:    {item['from']}")
    typer.echo(f"Subject: {item['subject']}")
    typer.echo(f"Stored:  {item['bucket']}")
    typer.echo(f"Now:     {bucket}")
    typer.echo(f"Reason:  {reason}")
    if bucket != item["bucket"]:
        typer.echo("(rules.yaml has changed since this message was classified)")


@app.command()
def suggest(
    home: Path = typer.Option(None, help="Override data directory."),
    min_occurrences: int = typer.Option(3, help="Minimum labels per pattern."),
) -> None:
    """Mine labels.jsonl for proposed rules.yaml additions."""
    home = home or _default_home()
    entries = labels_mod.load_all(home / "labels.jsonl")
    if not entries:
        typer.echo("No labels yet. Run 'morning-brief label' first.")
        raise typer.Exit(0)

    result = suggest_mod.suggest_additions(entries, min_occurrences=min_occurrences)
    if not any(result.values()):
        typer.echo(
            f"No clear patterns at min_occurrences={min_occurrences}."
            " Rate a few more messages or lower --min-occurrences."
        )
        raise typer.Exit(0)

    typer.echo(
        f"Proposed additions to rules.yaml"
        f" (min_occurrences={min_occurrences}, {len(entries)} labels):\n"
    )
    for key in (
        "high_priority_senders",
        "high_keywords",
        "spam_senders",
        "spam_keywords",
    ):
        vals = result.get(key, [])
        if not vals:
            continue
        typer.echo(f"{key}:")
        for v in vals:
            typer.echo(f'  - "{v}"')
        typer.echo("")
