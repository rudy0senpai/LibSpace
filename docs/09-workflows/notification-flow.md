# Notification Flow
**Status:** Planned
Event (due soon, overdue, reservation available, suggestion status change, new books) → `notification_service` creates a record for the recipient → UI polls/refreshes via `NotificationContext` → user marks read. Email is future scope.
