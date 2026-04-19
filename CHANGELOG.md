# Changelog

All notable changes to **morning-brief** are logged here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
morning-brief uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `.prsop.yml` and GitHub Actions workflow for PR governance via
  [pr-sop](https://github.com/Pawansingh3889/pr-sop).
- `CHANGELOG.md` tracking notable changes per release.

## [0.2.0] - 2026-04-19

### Added
- Rule-based classifier with HIGH, MEDIUM, LOW, SPAM buckets. Case-insensitive
  substring matching on sender and subject. Precedence: spam first, then high,
  then github-low, then medium.
- Gmail API read-only OAuth flow with a paste-the-URL fallback for WSL where
  the browser running on Windows cannot reach the Python callback server
  bound inside WSL.
- `morning-brief init` scaffolds `~/.morning-brief/` with a starter
  `rules.yaml`.
- `morning-brief run` fetches recent unread mail, classifies by rules, writes
  a markdown digest to `~/.morning-brief/digests/YYYY-MM-DD.md`, and fires a
  desktop notification.
- `morning-brief label` walks through today's classified messages one at a
  time and asks for a 1 to 5 star rating per message. Ratings persist as
  append-only JSONL.
- `morning-brief suggest` mines the label history for proposed additions to
  `rules.yaml` by sender domain average rating and subject keyword exclusivity.
- Cross-platform notifications: `winotify` on Windows, `wsl-notify-send` or
  `notify-send` on Linux, print-to-stdout as a fallback so nothing goes silent.
- 23 unit tests covering the classifier, label store, and pattern miner.

[Unreleased]: https://github.com/Pawansingh3889/morning-brief/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Pawansingh3889/morning-brief/releases/tag/v0.2.0
