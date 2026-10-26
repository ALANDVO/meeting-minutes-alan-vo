# Changelog

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [1.1.0] - 2026-10-16

## 1.1.0

- Add action status filter in the Minutes Panel to focus follow-through review on open, in-progress, blocked, done or cancelled actions.
- Decisions and questions are always shown; the filter only affects action items.
- Filter state resets when switching meetings for a clean context.
- Add action status counts in the filter dropdown showing the number of actions per status (e.g., "Open (3)", "In progress (1)").
- Counts only include action items, not decisions or questions.

## [1.0.0] - 2026-10-09

## 1.0.0

- Replace the CLI-only baseline with an authenticated full-stack meeting-record workspace.
- Add exact source citations, conservative deadline rules and human-corrected action/decision/question records.
- Add independent approval, immutable approved snapshots, transactional revisions and action status audit trails.
- Add safe Markdown, JSON, CSV, Slack text and calendar exports, bounded persistence and optional grounded model suggestions.
- Preserve the CLI commands with offline extraction and add backend, OIDC and frontend workflow tests plus a reproducible extraction diagnostic.
