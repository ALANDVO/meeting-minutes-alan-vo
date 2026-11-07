# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

status-capitalization-consistency

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

### action-status-counts — Action Status Counts in Filter Dropdown

Status: done

Acceptance:
- Filter dropdown shows action count per status (e.g., 'Open (3)', 'In progress (1)')
- Count updates when actions are added/removed/transitioned
- Count only includes action items, not decisions/questions
- 'All actions' shows total action count

Implementation: `frontend/src/MinutesPanel.tsx`

Tests: `frontend/src/workflows.test.tsx`

### filter-visibility-and-capitalization — Filter Bar Visibility and Status Capitalization

Status: done

Acceptance:
- Filter bar only renders when meeting has at least one action item
- Status badges and transition buttons show capitalized status labels (e.g., 'In Progress' instead of 'in progress')
- Consistent capitalization with filter dropdown option labels

Implementation: `frontend/src/MinutesPanel.tsx`

Tests: `frontend/src/workflows.test.tsx`

### status-capitalization-consistency — Status Capitalization Consistency Across Components

Status: done

Acceptance:
- Filter dropdown in Minutes Panel shows properly capitalized status labels (e.g., 'In Progress' instead of 'In progress')
- Item Editor status selector shows properly capitalized status labels matching badge display
- Consistent capitalization across all components using shared capitalizeStatus function

Implementation: `frontend/src/MinutesPanel.tsx`, `frontend/src/ItemEditor.tsx`

Tests: `frontend/src/workflows.test.tsx`

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
