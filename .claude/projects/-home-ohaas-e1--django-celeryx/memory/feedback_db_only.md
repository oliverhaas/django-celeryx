---
name: db-only-no-dual-store
description: Use database as single source of truth, no separate in-memory store
type: feedback
---

Do NOT maintain two separate data stores (in-memory ring buffer + database). Use a single database as the source of truth. If the user wants fast in-memory performance, they configure an in-memory SQLite database. The admin views should query the database directly, not a separate in-memory store.

**Why:** Maintaining two implementations (in-memory + DB) is complexity for no real benefit. SQLite in-memory is fast enough. One code path is better than two.

**How to apply:** Remove the in-memory TaskStore/WorkerStore. Event handlers write to DB only. Admin querysets read from DB only. The DATABASE setting should default to an in-memory SQLite configuration (not None).
