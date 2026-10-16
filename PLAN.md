# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

action-status-filter

## Roadmap

### action-status-filter — Action Status Filter in Minutes Panel

Status: done

Acceptance:
- MinutesPanel shows a filter control for action status (all, open, in_progress, blocked, done, cancelled)
- Filter applies to displayed actions only, not decisions/questions
- Selected filter persists during session
- Filter state resets when switching meetings
- Keyboard accessible with proper ARIA labels

Implementation: `frontend/src/MinutesPanel.tsx`

Tests: `frontend/src/workflows.test.tsx`

