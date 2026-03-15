---
name: copy-flower-layout
description: Always copy Flower's exact layout and columns, just restyle for Django admin
type: feedback
---

Worker/task list views should match Flower's columns and layout exactly, just restyled for Django admin. Don't invent different columns (like "pool", "concurrency") when Flower shows "succeeded", "failed", "retried". The general guideline is to copy Flower almost everywhere, just in Django admin styling.

**Why:** The user wants feature parity with Flower, not a reimagined version. The value proposition is "Flower but embedded in Django admin", not a different monitoring tool.

**How to apply:** When implementing any view (list or detail), first check what Flower shows for that exact page, then replicate those columns/fields/layout. Only deviate when there's a strong reason.
