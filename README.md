# Course 4 Supplement — Business & Transaction Systems

**Systems Thinking in the AI Era IV**

This repository contains the discovery labs and challenge templates for [Course 4: Business & Transaction Systems](https://systemthinkinglab.ai/course-4).

## What's in here

```
course4-supplement/
├── building_blocks/        Shared building block reference implementations
│   ├── building_blocks.py  Service, Worker, FileStore, KeyValueStore, Queue,
│   │                       RelationalDB, VectorDB (the 7 universal building blocks)
│   └── external_entities.py  User, External Service, Time
│
├── labs/course4/           Hands-on discovery labs
│   ├── lab1_service_relational_db.py          Service + Relational DB —
│   │                                          ACID, transactions, idempotency
│   └── lab2_service_external_service.py       Service + External Service —
│                                              payment integration, webhooks
│
└── challenges/course4/     Technical Design Document templates (Phase 5)
```

## Quick start

You need Python 3.8 or higher. No third-party packages are required: the labs use only the standard library.

```bash
git clone https://github.com/systemthinkinglab/course4-supplement.git
cd course4-supplement
python3 labs/course4/lab1_service_relational_db.py
```

## Running the labs

Each lab is interactive and self-contained. You'll be guided through three progressive experiments with 3 multiple-choice questions and educational feedback after each one.

### Lab 1 — Service + Relational Database (Business Logic Foundation)

```bash
python3 labs/course4/lab1_service_relational_db.py
```

Three experiments build deep intuition for why money math lives in the Relational Database:

1. **Atomic money movement** — perform a balance transfer without a transaction, watch a mid-flow crash leave money missing. Wrap the same flow in BEGIN/COMMIT/ROLLBACK and watch the ledger restore itself.
2. **Concurrent inventory** — two checkouts race for the last unit at default isolation; the lost-update bug fires. See three production-grade fixes side by side: SERIALIZABLE isolation, SELECT FOR UPDATE row locks, and optimistic compare-and-swap on a version column.
3. **Idempotency keys at the database** — a retried checkout without a UNIQUE constraint creates a duplicate order; with the constraint, the database refuses the duplicate insert and the Service replays the original result. Plus the Stripe-style payload-mismatch 409 contract.

```bash
# Run a single experiment
python3 labs/course4/lab1_service_relational_db.py 2

# Skip the typewriter effect (faster runs)
python3 labs/course4/lab1_service_relational_db.py --skip-typewriter

# Non-interactive mode (skips MC questions, runs the experiments end-to-end)
python3 labs/course4/lab1_service_relational_db.py --no-interactive
```

### Lab 2 — Service + External Service (Payment Integration Discovery)

```bash
python3 labs/course4/lab2_service_external_service.py
```

Three experiments build deep intuition for integrating with an External Service over the network:

1. **Sync vs Queue + Worker** — 10 checkouts each through a synchronous Service-to-processor call vs a Queue-mediated async pipeline. User-facing latency drops by ~100x once the External Service work moves off the request path; processor work itself is unchanged.
2. **Idempotency on timeout** — the processor charges the customer, but the response is lost on the network. Without an idempotency key, the retry double-charges. With one key per click-intent reused on every retry, the processor replays the original result. Payload mismatch returns 409.
3. **Webhook signature + replay protection** — three checks defeat three attacks. HMAC-SHA256 signature defeats forgeries. A Time-bounded replay window stops out-of-window replays. An event_id dedup set inside the window catches in-window replays.

```bash
# Run a single experiment
python3 labs/course4/lab2_service_external_service.py 3

# Skip the typewriter effect
python3 labs/course4/lab2_service_external_service.py --skip-typewriter

# Non-interactive mode
python3 labs/course4/lab2_service_external_service.py --no-interactive
```

## Challenge templates

Phase 5 of the course will publish three Technical Design Document templates here for the Course 4 Capstone Challenge: designing **FlexFund**, a consumer lending platform.

- **Part 1: MVP Foundation** — loan flow end to end, idempotent credit pull and disbursement, append-only audit log
- **Part 2: Compliance + Credit Engine** — Time-based loan lifecycle, deterministic Credit Engine Service, retry pipeline with dead-letter
- **Part 3: Audit + Risk** — regulatory reporting, anomaly detection with Vector Database similarity, multi-party dispute saga, adverse action notices

When the templates land, fill in each section using **building block names** (Service, Queue, Worker, Key-Value Store, File Store, Relational Database, Vector Database, External Service) and submit through the challenge form on the course site.

## Building block language

These labs and challenges teach you to think in **building blocks** rather than specific technologies. Use names like `Relational Database` instead of `Postgres`, `External Service` instead of `Stripe`, `Queue` instead of `Inngest`. The pattern is what matters; technology is implementation.

The labs themselves use simple Python primitives (sqlite3, hmac, hashlib, threading, queues) so the building-block semantics are visible without any managed-service magic. The same patterns map directly to Postgres on Supabase or Neon, to Stripe or Adyen for payments, and to Inngest or Trigger.dev for Queue + Worker pipelines when you wire this up at your job.

## Course site

Full course at [systemthinkinglab.ai/course-4](https://systemthinkinglab.ai/course-4).

## License

See [LICENSE](LICENSE).
