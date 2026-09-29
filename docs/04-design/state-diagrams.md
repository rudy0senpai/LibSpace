# State Diagrams
**Status:** Planned

## Loan
```mermaid
stateDiagram-v2
    [*] --> REQUESTED
    REQUESTED --> APPROVED
    REQUESTED --> CANCELLED
    APPROVED --> BORROWED
    BORROWED --> RETURNED
    BORROWED --> OVERDUE
    OVERDUE --> RETURNED
    BORROWED --> LOST
    BORROWED --> DAMAGED
```

## Book copy
`AVAILABLE`, `BORROWED`, `RESERVED`, `LOST`, `DAMAGED`, `MAINTENANCE`, `WITHDRAWN`. Typical path: AVAILABLE → BORROWED → AVAILABLE; a returned copy may go to DAMAGED/MAINTENANCE; retired copies become WITHDRAWN.

## Suggestion
```mermaid
stateDiagram-v2
    [*] --> SUBMITTED
    SUBMITTED --> UNDER_REVIEW
    UNDER_REVIEW --> APPROVED
    APPROVED --> ORDERED
    ORDERED --> AVAILABLE
    UNDER_REVIEW --> REJECTED
    UNDER_REVIEW --> DUPLICATE
    UNDER_REVIEW --> ALREADY_AVAILABLE
```
Exact allowed transitions are to be confirmed during design.
