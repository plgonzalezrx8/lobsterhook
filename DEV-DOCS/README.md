# DEV-DOCS - Lobsterhook

## Purpose
This folder is the engineering source of truth for Lobsterhook. It captures the current architecture, active work, coding rules, and reusable implementation notes for the Himalaya-backed email-to-webhook bridge.

## Reading Order
1. [00-START-HERE.md](./00-START-HERE.md)
2. [01-task-list.md](./01-task-list.md)
3. [DEVELOPMENT-STATUS.md](./DEVELOPMENT-STATUS.md)
4. [ARCHITECTURE.md](./ARCHITECTURE.md)
5. [project-structure.md](./project-structure.md)
6. [features/mailbox-polling.md](./features/mailbox-polling.md)
7. [features/outbound-webhook-delivery.md](./features/outbound-webhook-delivery.md)

## Folder Structure
```text
DEV-DOCS/
├── README.md
├── 00-START-HERE.md
├── 01-task-list.md
├── ARCHITECTURE.md
├── CODING-STANDARDS.md
├── DEVELOPMENT-STATUS.md
├── ENV-CONTRACT.md
├── NEW-FILES-GUIDE.md
├── SECURITY-GUIDELINES.md
├── TESTING-PERFORMANCE.md
├── project-structure.md
├── work-log.md
├── features/
│   ├── mailbox-polling.md
│   └── outbound-webhook-delivery.md
└── implementation/
    ├── himalaya-adapter.md
    ├── local-storage-and-normalization.md
    └── sqlite-queue-and-idempotency.md
```

## Conventions
- Update these docs in the same change set as behavior changes.
- Keep current-state facts separate from planned work.
- Prefer concrete file paths, commands, config keys, and database tables.
- Treat feature docs as behavior contracts and implementation docs as reusable technical patterns.
