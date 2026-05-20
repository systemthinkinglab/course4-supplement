# Challenge 4 Part 2: Technical Design Document - Compliance and Credit Engine

**Student Name**: [Your Name]
**Submission Date**: [Date]
**Challenge**: FlexFund Fintech Lending Platform - Part 2 Compliance and Credit Engine

---

## Context: what happened

Your Part 1 MVP launched. A year later, FlexFund is no longer launching, it is operating. Loan volume is up. A compliance officer joined the company and is asking pointed questions about the audit trail. The auditors are coming next quarter. The data science team is building an ML model and the CFO wants the credit engine to plug it in without an architectural rewrite. Operations has noticed that the payment processor has bad afternoons where two or three percent of disbursements fail and need to retry. The loan is no longer a one-time event. It has a life that runs on a billing clock, with monthly statements, late fees on delinquency, and lifecycle states (current, late, delinquent, default).

This document is your **evolution** of the Part 1 design, not a redesign. The Part 1 architecture stays intact. New blocks join it. Time enters as a first-class external entity. File Store enters for compliance artifacts. The grader runs the full Part 1 rubric against your Part 2 submission and penalizes regressions.

## IMPORTANT: Technology-Agnostic Design Required

Use building block names, not technologies. See the Part 1 template for the full list. Hash chains, append-only constraints, role-based database privileges, transactional outbox, exponential backoff, and dead-letter queues are all **patterns**, not products. Name the pattern; do not name a vendor.

---

## Part 1 Architecture Recap

[Briefly summarize your Part 1 architecture in 2-3 sentences. Name the major components: Application Service, Credit Pull Queue + Credit Worker, Decision Service, Relational Database for applications and decisions, Relational Database (append-only) for the audit log, Disbursement Queue + Disbursement Worker with persist-intent-first idempotency, External Services for credit bureau and payment processor, File Store for identity documents, Relational Database for the loan ledger at a strict isolation level. This is the foundation Part 2 stands on.]

---

## Requirement 1: Immutable Audit Log

*Every decision, every external call, every state change is logged to an append-only audit trail. The log cannot be edited or deleted within the retention window. A cryptographic hash chain (each row hashes the previous row) makes tampering mathematically detectable. The Decision Service writes the decision row and the audit row in one database transaction. A separate Audit Worker reads from the outbox and propagates downstream.*

### User Flow Design

```
Example formats:
Decision + audit write: Decision Service → Relational Database (decision row + audit row, one transaction)
Audit outbox: Relational Database (outbox table) → Audit Worker → downstream consumers
Hash chain compute: Audit Worker (or inline trigger) → previous row hash + current row contents → audit row hash
Retention sweep: Time → Retention Worker (separate database role with scoped DELETE) → Relational Database
```

**Your immutable audit flows:**
[Write 3-5 specific flows for the decision-plus-audit transactional write, the Audit Worker propagating downstream, the hash chain construction, and the role-scoped retention sweep.]

### Building Blocks Added

- **[Audit Worker]**: [Reads from the transactional outbox. Propagates audit events to downstream consumers (analytics warehouse, regulator-facing reports, real-time compliance monitoring). Worker failure does not block the user's transaction.]
- **[Retention Worker]**: [Runs on Time. Uses a separate database role with DELETE scoped only to expired rows. The application role never has DELETE on the audit table.]
- **[Audit event Queue]**: [Between the outbox and the Audit Worker, if your design uses an explicit Queue. Or the outbox table itself is the Queue.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Name the mechanism that makes the audit log append-only at the database level. INSERT-only role privileges? An append-only table constraint? Both?]
- **[Decision 2]**: [Why does the decision write and the audit write commit in the same transaction? This is the transactional outbox pattern. Name it. State what goes wrong if the two commits happen independently.]
- **[Decision 3]**: [How does the hash chain work? Each row contains a hash of the previous row's contents. Tampering with row N invalidates every hash from N+1 onward. What does the chain protect against that role-based privileges do not?]

### Technical Implementation Details

**Database role discipline**: [Name the roles. Application role: INSERT and SELECT on the audit table, nothing else. Retention role: DELETE scoped only to expired rows. State the role boundaries explicitly.]

**Transactional outbox commitment**: [Confirm the decision row and the audit row commit in the same database transaction. State the seam: if the audit write fails, the business write rolls back.]

**Hash chain construction**: [What goes into the hash? Previous row hash + current row contents (canonicalized)? Where is the chain head stored? How does an auditor verify the chain end to end?]

**Retention window**: [How long are audit rows retained before the Retention Worker can delete them? Defend the window with the regulatory constraint that drives it.]

---

## Requirement 2: Credit Engine + Rule Service

*Replace the inline scoring from Part 1 with a Credit Engine Service that applies versioned, configurable rules and can call an ML External Service for probabilistic inputs. The engine must be deterministic: same inputs plus same rule-set version plus same model version produces same output. Past decisions must be reproducible from the audit log.*

### User Flow Design

```
Example formats:
Engine call: Decision Service → Credit Engine Service → Rule Service (rule-set version N) → External Service (ML model version M) → composite score
Decision record: Credit Engine Service → audit log (rule-set version, model version, inputs hash, outputs)
Replay: Auditor → Replay Service → Relational Database (audit log entry) → Credit Engine Service (with pinned versions) → same output
```

**Your credit engine flows:**
[Write 3-5 specific flows showing how the Decision Service calls the Credit Engine, how the engine composes rule-based and ML-based signals, how every version is recorded in the audit log, and how an auditor replays a past decision.]

### Building Blocks Added

- **[Credit Engine Service]**: [The orchestrator. Calls the Rule Service and the ML External Service. Composes a final score and decision. Records every version.]
- **[Rule Service]**: [Holds the versioned rule sets. A rule-set version is an immutable artifact, pinned per decision.]
- **[External Service - ML model]**: [The cloud ML model. Versioned. Every call records the model version alongside the result.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why is the engine a separate Service from the Decision Service? What seam does that separation enable for Part 3 (anomaly detection, risk scoring)?]
- **[Decision 2]**: [How are rule sets versioned? A version column on each rule? A signed bundle? Defend the shape that makes replay deterministic.]
- **[Decision 3]**: [What does "deterministic" mean in this design? Same input plus same rule-set version plus same model version produces same output. Name what the audit log must record to make this provable two years later.]

### Technical Implementation Details

**Rule-set versioning**: [Name the concrete versioning shape. Semantic version? Content hash? Both?]

**ML model versioning**: [Every ML External Service call records the model version on the response. The Credit Engine writes that version to the audit log for the decision.]

**Replay mechanism**: [How does an auditor replay a past decision? The audit log holds inputs + rule-set version + model version. The replay path pins those versions and recomputes. What is the guarantee on equality?]

**Composition rule**: [How does the engine combine rule-based signals with ML probabilistic signals? Weighted? Rule-based veto on ML? Name the composition rule.]

---

## Requirement 3: Payment Retry Pipeline

*A failed disbursement or repayment retries with exponential backoff. After N attempts, it moves to a dead-letter Queue for human review. The same idempotency key is used on every retry so the payment processor never disburses twice. The retry pipeline holds the same key for the lifetime of the disbursement, not the lifetime of the attempt.*

### User Flow Design

```
Example formats:
First attempt: Disbursement Worker → External Service (payment processor, same key) → failure
Retry enqueue: Disbursement Worker → Retry Queue (with delay)
Retry: Retry Queue (delayed) → Retry Worker → External Service (same key) → outcome
Dead-letter: After N attempts → Dead-Letter Queue → human review
```

**Your retry pipeline flows:**
[Write 3-5 specific flows showing the first attempt failure, the retry enqueue with delay, the retry call with the same key, and the dead-letter destination.]

### Building Blocks Added

- **[Retry Queue]**: [Delayed Queue for failed payments. Workers pull from it after the delay has elapsed.]
- **[Retry Worker]**: [Picks up failed payments after a delay, calls the processor with the same idempotency key, and either succeeds or schedules the next retry with a longer delay.]
- **[Dead-Letter Queue]**: [Separate destination. After N attempts, the payment lands here for human operators. A retry loop with no dead-letter is operationally dangerous.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Name the exponential backoff schedule. 1 minute, 5 minutes, 30 minutes, 2 hours, dead-letter, or some other curve? Defend the shape.]
- **[Decision 2]**: [Why is the idempotency key bound to the disbursement, not the attempt? State the failure mode that a per-attempt key would cause.]
- **[Decision 3]**: [The Lesson 1 idempotency key has four properties. The two that bite hardest in a retry pipeline: TTL (if a retry fires after the processor evicted the key, the second call is a new intent) and persist-intent-first (write the intent and key in your Relational Database transaction before the first call). Name how your retry pipeline honors both.]

### Technical Implementation Details

**Backoff schedule**: [Commit to a concrete schedule. Name the boundary between "transient, will retry" and "stuck, move to dead-letter".]

**Same-key invariant**: [The same idempotency key is used on every retry of the same disbursement. State the invariant. State how the Retry Worker reads the key from the Relational Database intent row, not from in-memory state.]

**TTL handling**: [What does the design do if a manual retry fires days after the processor evicted the key? Generate a fresh key? Read the original outcome from your Relational Database and short-circuit?]

**Dead-letter handling**: [What happens when a payment lands in the dead-letter Queue? Who reviews it? Does the audit log record the move to dead-letter as its own event?]

---

## Requirement 4: Time-Based Loan Lifecycle

*Statement generation runs on a monthly clock. Delinquency thresholds trigger late fees. The loan moves through lifecycle states (current, late, delinquent, default) on a schedule. Time is the external entity that fires the work. Signed loan agreements and generated statements live in File Store.*

### User Flow Design

```
Example formats:
Statement run: Time → Statement Worker → Relational Database (ledger) → File Store (statement PDF) → External Service (notification gateway)
Delinquency check: Time → Delinquency Worker → Relational Database (ledger walk) → state transition + audit entry + late fee
Lifecycle audit: Every transition → Audit Worker → audit log
```

**Your time-driven lifecycle flows:**
[Write 3-5 specific flows for the monthly statement run, the delinquency walk, and every lifecycle-state transition. Be explicit about which Worker fires on which Time cadence.]

### Building Blocks Added

- **[Time external entity]**: [The trigger for statement generation, delinquency checks, and retention sweeps. Name the cadence for each.]
- **[Statement Worker]**: [Runs on Time. Reads the ledger. Generates the statement file. Writes the file to File Store. Sends notification through an External Service.]
- **[Delinquency Worker]**: [Runs on Time. Walks the ledger. Moves loans through lifecycle states. Applies late fees. Audit-logs every transition.]
- **[File Store]**: [Holds signed agreements and generated statements. The Relational Database indexes the files by loan ID and statement period.]
- **[External Service - notification gateway]**: [Delivers the statement notification. Idempotency key per statement-per-loan.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why Time as the external entity, named explicitly, rather than describing the Workers as "scheduled"? The grader treats cron-like scheduling without naming Time as a miss.]
- **[Decision 2]**: [When does a delinquency state transition happen relative to Time firing? Is the loan in "late" at the moment the Worker runs, or at the moment the due date passed? State the rule.]
- **[Decision 3]**: [What idempotency key shape protects the statement notification? A retry from the Statement Worker must not produce two statements for the same loan-period.]

### Technical Implementation Details

**Time cadence**: [Statement Worker fires monthly. Delinquency Worker fires daily, or hourly? Name the cadence per Worker.]

**Statement file shape**: [What lands in File Store? A generated PDF? An HTML rendering? The Relational Database holds a pointer with statement-period, loan-id, and generation timestamp.]

**Lifecycle state machine**: [Name the states (current, late, delinquent, default) and the transitions. Every transition is audit-logged. State the rule for late-fee application.]

**Idempotency for statement notification**: [Name the key shape. Per-loan-per-statement-period is the natural choice.]

---

## Requirement 5: Compliance Trade-offs

*The design explicitly addresses two of the three tensions compliance introduces: speed of UX versus audit-log durability, automation versus human review, and fraud detection latency versus accuracy. Name two trade-offs you made, what you gave up, and what you gained.*

### Trade-off 1: [Name the trade-off]

**The tension**: [State the tension in one sentence. Example: "Audit-first writes slow the user's request because the ledger write and the audit entry commit together."]

**The choice you made**: [State your choice. Example: "Audit-first, every time. The user-facing latency penalty is acceptable. A faster path that occasionally loses an audit row is not."]

**What you gave up**: [The cost in concrete terms. Example: "Added 30-50ms to every ledger write."]

**What you gained**: [The benefit in concrete terms. Example: "Every state change is reconstructable from the audit log. A regulator can prove correctness without trusting the application's own bookkeeping."]

**Where in the design this lives**: [Name the seam. Example: "The Decision Service and the Ledger Service both write the business row and the audit row in the same database transaction."]

### Trade-off 2: [Name the trade-off]

**The tension**: [State the tension in one sentence.]

**The choice you made**: [State your choice.]

**What you gave up**: [The cost in concrete terms.]

**What you gained**: [The benefit in concrete terms.]

**Where in the design this lives**: [Name the seam.]

---

## Foundation Preserved

Walk through the Part 1 paths and confirm they are intact. The grader checks for regressions and penalizes them twice.

- **Application + identity intake**: [Application Service + File Store still in place?]
- **Credit pull**: [Credit Pull Queue + Credit Worker + External Service (credit bureau) with concrete idempotency key still wired?]
- **Decision persistence**: [Decision Service + Relational Database still the system of record?]
- **Audit log architectural separation**: [Audit table still separate; Part 2 only strengthened it with role discipline and hash chain.]
- **Disbursement**: [Disbursement Worker + External Service (payment processor) with persist-intent-first and per-disbursement key still wired?]
- **Ledger**: [Relational Database at strict isolation level still the system of record?]

---

## Cross-Cutting Trade-offs

A strong Part 2 names where the new requirements collide with the Part 1 design.

### Audit durability vs UX latency

[The transactional outbox slows every write. State where in the design the latency tax falls hardest, and defend the cost.]

### Determinism vs ML model freshness

[An ML model that updates without versioning breaks determinism. State how the Credit Engine pins versions and what cost that imposes on the data science team's release cadence.]

### Retry aggressiveness vs processor goodwill

[An aggressive retry schedule recovers faster but burns processor quota. State your backoff curve and what it optimizes for.]

### Time-driven correctness vs operational complexity

[Time-driven Workers introduce a new failure mode: what if a Worker misses a fire? State how the design detects and recovers from a missed cadence.]

---

## Failure Mode Analysis

Name what still breaks and how the system degrades:

- **If the Audit Worker is down**: [Does the user's transaction still complete? The outbox holds the events; the Audit Worker drains when it recovers. State the lag tolerance.]
- **If the ML External Service is unavailable**: [Does the Credit Engine fall back to rule-only scoring? Does it record the fallback in the audit log so a future audit knows the decision did not use ML?]
- **If the Retry Queue backs up**: [What happens to the payment SLA? Does the dead-letter Queue catch the truly stuck payments? How does operations see the backlog?]
- **If the Statement Worker crashes mid-run**: [What state are the partially generated statements in? Is the run idempotent so a re-run on the next Time fire completes the remaining loans?]
- **If the hash chain is broken on row N**: [What does the system do? Refuse all subsequent reads? Surface a compliance alert? State the response.]

---

## Trade-offs Explicitly Accepted

- **[Trade-off 1]**: [What you gave up to add these capabilities]
- **[Trade-off 2]**: [What you gave up to add these capabilities]
- **[Trade-off 3]**: [What you gave up to add these capabilities]

---

## What This Evolution Intentionally Does NOT Address

[Anything you are deferring to Part 3. Be explicit. Examples: multi-state regulatory reporting, anomaly detection with ML and Vector Database, multi-party dispute saga with compensating actions, risk reasoning artifacts, adverse action notice pipeline. The grader rewards designs that know their boundaries.]

---

## Self-Graded Rubric (A / A- / B+)

**My grade**: [A / A- / B+]

**Why I assigned this grade**: [Apply the same rubric from Lesson 2. A means all five new requirements covered + transactional outbox named + hash chain named + Credit Engine with version pinning + retry pipeline with concrete backoff and dead-letter + Time-driven Workers + two compliance trade-offs explicitly defended + Part 1 preserved. A- means strong with one precision gap (example: backoff curve named but dead-letter not explicit). B+ means solid but missing one of the named patterns. Be honest.]

---

## Submission

Save this document as markdown and paste the full content into the **Challenge Part 2** submission form at [systemthinkinglab.ai](https://systemthinkinglab.ai/protected/course4/challenge2.html). Part 1 must be graded before Part 2 can be submitted.
