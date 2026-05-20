# Challenge 4 Part 3: Technical Design Document - Audit and Risk

**Student Name**: [Your Name]
**Submission Date**: [Date]
**Challenge**: FlexFund Fintech Lending Platform - Part 3 Audit and Risk

---

## Context: the final evolution

FlexFund has been operating for several years. The regulator has approved the company to operate in multiple states. A risk team exists. A collections operation exists. Disputes happen weekly, sometimes daily, and a small number of them escalate to regulator involvement. The product team has one more push. They want the platform to be a fully regulated operation. Monthly regulatory submissions through an External Service the regulator provides. Portfolio-level anomaly detection that combines an ML External Service for default scoring with a Vector Database for similarity search against historical defaults. A multi-party dispute workflow that tracks customer, lender, collections, and regulator interactions through a saga-style state machine. The thirty-day Fair Credit Reporting Act and Equal Credit Opportunity Act clock on adverse action notices.

This is the capstone of the four-course series. By the end of Part 3, all seven building blocks should appear in your design with a clear job. Vector Database finally has a real role. The Part 1 and Part 2 designs survive intact. The grader runs the full rubric for all three parts.

## IMPORTANT: Classification Matters Here

The regulator's submission endpoint is an **External Service**. Not a Service you own. The ML model for default scoring is an **External Service**. The notification provider for adverse action notices is an **External Service**. The credit bureau and payment processor from Parts 1 and 2 are still External Services.

The Vector Database is a **Vector Database**. Embeddings of past defaulted loans live there. Not in a Relational Database. Not in a Key-Value Store. The grader will check this classification: it is part of the grade.

Sagas are a **pattern**, not a building block. A saga is a sequence of Worker steps with explicit compensation paths. The compensation Workers are Workers. The compensation calls go through the same External Services. The state of the saga lives in the Relational Database.

Use building block names. No vendor names. See the Part 1 template for the full discipline.

---

## Part 1 and Part 2 Architecture Recap

[Briefly summarize the architecture after Part 2 (2-3 sentences). Part 1: Application Service, Credit Pull Queue + Worker calling credit bureau External Service with per-application idempotency, Decision Service, append-only audit table, Disbursement Worker with persist-intent-first per-disbursement key calling payment processor External Service, Relational Database ledger at strict isolation level. Part 2: transactional outbox + Audit Worker + hash chain, Credit Engine Service + Rule Service + ML External Service with version pinning, Retry Queue + Worker + Dead-Letter Queue with exponential backoff, Time-driven Statement Worker + Delinquency Worker writing to File Store. This is the foundation that survives.]

---

## Requirement 1: Regulatory Reporting Pipeline

*Every month (and on whatever cadence the regulator requires) the platform aggregates the loan portfolio (origination volumes, repayment status, demographic breakdowns, default rates) and submits a report to a regulator's External Service. The submission is idempotent. Every submission and every retry lands in the audit log. The report file is preserved in File Store for historical access. Three audit events per report: assembled, sent, acknowledged.*

### User Flow Design

```
Example formats:
Report assembly: Time → Reporting Worker → Relational Database (portfolio aggregates) → File Store (report file)
Report submission: Reporting Worker → External Service (regulator) → acknowledgment → audit log
Retry on failure: Reporting Worker → Retry Queue → External Service (same idempotency key) → outcome
Audit trail: Three events per report (assembled, sent, acknowledged) → Audit Worker → audit log
```

**Your regulatory reporting flows:**
[Write 3-5 specific flows for the Time-fired report assembly, the File Store write, the regulator submission with idempotency key, the retry on network failure, and the three audit events.]

### Building Blocks Added

- **[Reporting Worker]**: [Runs on Time. Reads from the Relational Database (and File Store for historical aggregates if your design holds historical snapshots there). Assembles the report into the File Store. Calls the regulator External Service with an idempotency key.]
- **[External Service - regulator]**: [The regulator's submission endpoint. Same reliability constraints as a payment gateway. Network failures happen. Duplicates are not acceptable.]
- **[File Store retention tier]**: [Holds the historical report files. Retention is regulatory, often years.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Name the idempotency key strategy on the regulator submission. A per-period-per-report-type key is the natural choice. Defend the shape.]
- **[Decision 2]**: [Why does the Worker assemble the report into File Store BEFORE calling the regulator? What goes wrong if the design calls the regulator first and saves the file on success?]
- **[Decision 3]**: [What does the system do if the regulator acknowledges asynchronously, hours later? How does the "acknowledged" audit event land if the original Worker run has long completed?]

### Technical Implementation Details

**Idempotency key shape**: [Commit to a concrete shape. Example: `regulatory_report:{report_type}:{period_start}` where `period_start` is a canonicalized date.]

**Three audit events**: [Name them: assembled (file written to File Store with content hash), sent (External Service call placed with key), acknowledged (regulator confirmed receipt). State the timestamp on each.]

**File Store retention**: [How long? What enforces the retention boundary?]

**Replay**: [If the regulator requests a historical report, how does the system regenerate it deterministically? The audit log holds the inputs; the same aggregation logic produces the same file. Confirm.]

---

## Requirement 2: Anomaly Detection

*The risk team wants suspicious loans flagged for review. Two signals combine: an ML External Service scores loans for default probability, and a Vector Database stores embeddings of past defaulted loans for similarity search. A loan whose pattern matches several past defaults gets flagged. Flagged loans surface in a review Queue for the risk team. The flag itself is audit-logged.*

### User Flow Design

```
Example formats:
Anomaly scan: Time → Anomaly Worker → Relational Database (current loan portfolio) → External Service (ML default scoring)
Similarity search: Anomaly Worker → embedding for current loan → Vector Database (top-k matches against past defaults)
Flag composition: Anomaly Worker combines ML score + similarity matches → Anomaly Review Queue → Risk Service
Audit entry: Every flag → Audit Worker → audit log
```

**Your anomaly detection flows:**
[Write 3-5 specific flows for the Time-driven scan, the ML scoring call, the Vector Database similarity search, the flag composition rule, and the path to the risk team's review Queue.]

### Building Blocks Added

- **[Anomaly Worker]**: [Runs on Time. Scores loans through the ML External Service and queries the Vector Database for similar past defaults.]
- **[External Service - ML default scoring model]**: [Distinct from the Credit Engine's underwriting ML model. This one scores active loans for default probability, not new applications for approval.]
- **[Vector Database]**: [Stores embeddings of past defaulted loans. The first place in the four-course series where Vector Database has a real job.]
- **[Anomaly Review Queue]**: [Flagged loans land here. The risk team's review tool reads from this Queue.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why does anomaly detection combine ML scoring with Vector Database similarity, and not just one or the other? State what each signal catches that the other misses.]
- **[Decision 2]**: [What is the embedding pipeline for past defaults? When a loan defaults, is the loan's feature vector written to the Vector Database immediately, or batch-embedded by a separate Worker?]
- **[Decision 3]**: [If the ML External Service is down, what does anomaly detection fall back to? Pure similarity search? Disable anomaly scans and surface a compliance alert? Defend the choice.]

### Technical Implementation Details

**Vector Database role**: [State the role in one sentence. Embeddings of past defaulted loans for similarity search against active loans. This is the requirement that earns the Vector Database its place in the design.]

**ML vs similarity composition**: [How does the Anomaly Worker combine the two signals? Weighted score? Either-or veto? State the rule.]

**Time cadence**: [How often does the Anomaly Worker fire? Hourly? Daily? Defend the cadence against the cost of an ML call per loan.]

**Audit on flag**: [Every flag is an audit event. State the event shape: loan ID, ML score, top-k similarity matches, composite decision, Worker version.]

---

## Requirement 3: Dispute Workflow

*A customer raises a dispute. The dispute can involve up to four parties: customer, lender, collections, and regulator. The workflow is a state machine. Every state transition is tracked. Every piece of evidence is preserved. Dispute state belongs in the Relational Database, not in a Key-Value Store. The Key-Value Store can cache the current state for fast display, but the system of record is the Relational Database.*

### User Flow Design

```
Example formats:
Dispute open: User → Dispute Service → Relational Database (dispute row + first transition)
Evidence upload: User → Dispute Service → File Store (evidence file) → Relational Database (file pointer)
State transition: Dispute Service → Relational Database (new transition row) → Dispute Event Queue → Audit Worker + notification Workers
Notification: Dispute Event Queue → Notification Worker → External Service (per party)
Display cache: Dispute Service → Key-Value Store (current state cache)
```

**Your dispute workflow flows:**
[Write 3-5 specific flows for opening a dispute, attaching evidence, transitioning state, notifying each party, and reading the current state for fast display.]

### Building Blocks Added

- **[Dispute Service]**: [Orchestrates the workflow. Owns the state machine logic. Coordinates the Relational Database, File Store, and Dispute Event Queue.]
- **[Relational Database for dispute state]**: [The system of record. Stores the current state, the full transition history, and pointers to evidence files.]
- **[File Store for evidence]**: [Holds evidence files attached at each transition. Files are indexed in the Relational Database by dispute ID.]
- **[Dispute Event Queue + Notification Workers]**: [Carries dispute events to the Audit Worker and to notification Workers that call External Services for each party.]
- **[External Services per party]**: [Customer notification gateway, lender ops channel, collections notification, regulator submission endpoint. Each is an External Service with idempotent calls.]
- **[Optional Key-Value Store]**: [Caches the current dispute state for fast display. Cache, not system of record.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Where does dispute state live as system of record, and what role does the Key-Value Store play if any? State the rule: Relational Database is the source of truth; Key-Value Store is a display cache only.]
- **[Decision 2]**: [How does the design preserve every piece of evidence across the four parties? File Store holds the bytes, Relational Database holds the pointers, audit log holds the lineage. State the boundary.]
- **[Decision 3]**: [What ACID isolation level does the dispute state machine run at, and why? Defend it against the trade-off (stronger isolation costs concurrency).]

### Technical Implementation Details

**State machine states**: [Name the states. Example: opened, customer_response_pending, lender_review, collections_escalation, regulator_review, resolved_for_customer, resolved_for_lender, closed.]

**Transition table**: [What does a transition row look like? from_state, to_state, actor, timestamp, evidence_pointer, audit_link.]

**Evidence integrity**: [Files in File Store are immutable. The Relational Database pointer carries the content hash so the audit log can prove the file was not swapped.]

**Notification idempotency**: [Each notification External Service call carries an idempotency key. Per-dispute-per-transition-per-party is the natural shape.]

---

## Requirement 4: Multi-Party Saga

*The dispute workflow is a saga. Every action that can be reversed must have an explicit compensation path. If the dispute resolves in the customer's favor and fees must be waived, the compensation runs through the same Worker pipeline, with its own idempotency key, audit-logged like every other action. Two-phase commit (2PC) is NOT the pattern here. The parties are external; you cannot hold a distributed lock across them. The saga pattern with compensating actions is the right choice. Defend that rationale.*

### User Flow Design

```
Example formats:
Forward action: Dispute Service → Worker → External Service (payment processor, e.g., fee charge) → audit entry
Compensation: Dispute resolves in customer's favor → Compensation Worker → External Service (payment processor, refund call) → audit entry linked to original
Saga state: Each step records its forward action and its compensation pointer in the Relational Database
```

**Your saga flows:**
[Write 3-5 specific flows for a forward action (fee charge, lien placement, collections handoff) and its compensation (refund, lien release, collections recall). State how each compensation is audit-logged and linked to the original.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [Why a saga with compensating actions, NOT 2PC? State the constraint that rules out 2PC: the parties are external; the platform cannot hold a distributed lock across the customer, the payment processor, the collections operation, and the regulator.]
- **[Decision 2]**: [What is the explicit compensation path for a dispute resolved in the customer's favor? Name the Worker, the idempotency key, and the audit entries.]
- **[Decision 3]**: [What happens if a compensation itself fails? Does the saga retry the compensation? Move to a compensation dead-letter Queue? State the rule.]

### Technical Implementation Details

**Forward action shape**: [Every forward action records: actor, External Service called, idempotency key used, outcome, audit entry pointer.]

**Compensation action shape**: [Every compensation records: the forward action it reverses, the External Service called (typically the same one with a refund or reversal endpoint), its own idempotency key (distinct from the forward key), and an audit entry linked to the original.]

**Saga state in Relational Database**: [The dispute row holds a list of completed forward actions and a list of completed compensations. The state machine knows which forward actions still need compensation if the dispute resolves in the customer's favor.]

**Compensation idempotency**: [The compensation Worker uses the same External Service (e.g., payment processor) with a new idempotency key per compensation. The compensation key is bound to the dispute resolution, not the original action.]

---

## Requirement 5: Risk Reasoning

*The design names when to deny a loan, when to escalate to manual review, and how the denial is itself audit-logged. The decision is reproducible from the audit log. The risk team can investigate any denial months later and reconstruct what the system saw and what rule fired. Every denial records the rule-set version, the model version, the credit-bureau result hash, and the score that triggered the denial. Escalation to manual review is its own state, not a side effect.*

### User Flow Design

```
Example formats:
Denial write: Decision Service → Relational Database (denial row + audit entry, one transaction)
Audit linkage: Denial audit entry carries rule-set version, model version, credit-bureau result hash, triggering score
Manual review escalation: Decision Service → state = manual_review → review Queue → Risk Service
Reconstruction: Auditor → Replay Service → audit log entry → Credit Engine Service (with pinned versions) → same denial output
```

**Your risk reasoning flows:**
[Write 3-5 specific flows for a denial write, a manual-review escalation, and a months-later audit reconstruction. State explicitly what is recorded so the reconstruction is deterministic.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [What does every denial record so it is reproducible months later? Name the four things at minimum: rule-set version, model version, credit-bureau result hash, triggering score. Add anything else your design captures.]
- **[Decision 2]**: [Why is manual review its own state in the Decision Service's state machine, not a side effect? State what goes wrong if escalation is a side effect (the audit log loses the escalation event).]
- **[Decision 3]**: [The audit trail of denials is a regulator-readable artifact. A denial the system cannot defend is a denial the company cannot defend. State the design discipline that makes every denial defensible.]

### Technical Implementation Details

**Denial audit row shape**: [Name every field. timestamp, applicant ID, decision_outcome (deny), rule_set_version, model_version, credit_bureau_result_hash, triggering_score, manual_review_flag.]

**Manual review state**: [Manual review is a state in the Decision Service's state machine. The transition into manual review and the transition out (approve, deny after human review) are both audit events.]

**Reconstruction guarantee**: [How does the system prove that "the same denial would have been made"? The audit log holds the inputs and the pinned versions. The Credit Engine, re-run with those pinned versions on those inputs, produces the same output.]

---

## Requirement 6: Adverse Action Notices

*When the platform denies a loan application, US federal law (the Fair Credit Reporting Act and the Equal Credit Opportunity Act) requires sending a written adverse action notice to the applicant within thirty days, stating the specific principal reason for the denial and the credit-bureau information the decision relied on. An Adverse Action Worker runs on Time, scans recent denials whose notice has not yet been generated, assembles the notice from the audit-log entry for that decision, writes the file to File Store, and delivers the notice through an External Service. The thirty-day clock must not slip if the Worker crashes mid-batch.*

### User Flow Design

```
Example formats:
Notice generation: Time → Adverse Action Worker → Relational Database (recent denials without notice) → audit log (decision entry) → File Store (notice PDF)
Notice delivery: Adverse Action Worker → External Service (notification provider) with idempotency key → Relational Database (delivery status: pending, sent, bounced)
Delivery confirmation: External Service callback or polling → Relational Database (status = delivered) → audit log
Three audit events: assembled, sent, delivered (the External Service confirmed actual delivery, not queue acceptance)
```

**Your adverse action notice flows:**
[Write 3-5 specific flows for the Time-fired scan, the audit-log read for the principal reason, the notice file write, the External Service delivery call, and the delivery confirmation that flips status from "sent" to "delivered".]

### Building Blocks Added

- **[Adverse Action Worker]**: [Runs on Time. Scans recent denials whose notice has not yet been generated. Reads the audit log entry for the decision. Assembles the notice. Writes the file to File Store. Calls the External Service for delivery.]
- **[File Store for notice files]**: [Holds the PDF notice. Indexed in the Relational Database by application ID.]
- **[Relational Database for delivery status]**: [Tracks the per-notice state: pending, sent, bounced, delivered. The "sent" state means the External Service accepted the call. The "delivered" state means the provider confirmed actual delivery.]
- **[External Service - notification provider]**: [Email or postal mail provider. Idempotent calls with per-notice key.]

### Architecture Decisions & Trade-offs

- **[Decision 1]**: [How does the Adverse Action Worker guarantee the thirty-day clock cannot slip if it crashes mid-batch? State the rule: the Worker reads denials whose notice_status is pending and whose denial date is within the window. A crash mid-batch leaves the unprocessed denials in pending; the next Time fire picks them up. The Worker is idempotent per denial.]
- **[Decision 2]**: [What is the idempotency key on the External Service delivery call? Per-notice is the natural shape. State why a per-attempt key would risk duplicates.]
- **[Decision 3]**: [Why does the design track both "sent" and "delivered" states? The first is a queue acceptance; the second is a provider confirmation. State the failure mode that conflating them would cause.]

### Technical Implementation Details

**Audit log as source of truth**: [The notice cannot reference a denial reason that does not appear in the audit log for that decision. The audit log is the constraint that bounds what the notice can say. State this discipline explicitly: this is why Part 1's audit log shape mattered and why Part 2's hash chain mattered.]

**Notice file shape**: [What lands in File Store? A PDF. The Relational Database holds the pointer with application ID, generation timestamp, and content hash.]

**Three states per notice**: [pending (queued), sent (External Service accepted), delivered (provider confirmed). State the transitions.]

**Idempotency key**: [Per-notice. Example: `adverse_action_notice:{application_id}`. A retry uses the same key. The provider returns the original delivery outcome.]

**Thirty-day window guarantee**: [The Adverse Action Worker fires daily (or at a cadence that gives margin). A denial dated day 0 has its notice generated, sent, and delivery-confirmed well within the thirty-day FCRA/ECOA window. State the operational margin (example: generate by day 7, confirmed-delivered by day 14).]

---

## The Three Classic Trade-offs

A strong Part 3 submission names these explicitly.

### Idempotency cost vs duplicate-prevention guarantee

[Every External Service call (regulator, ML, payment processor, notification provider, credit bureau) carries an idempotency key. The cost is the per-call key generation, persistence, and lookup. The guarantee is that no retry ever produces a duplicate. State where the cost is highest and defend it.]

### Determinism vs operational flexibility

[Every decision pins a rule-set version and a model version. This makes replay deterministic. The cost is that the data science team cannot silently update the model. State the operational discipline that this trade-off forces on releases.]

### Saga compensation cost vs cross-service atomicity

[A saga with explicit compensation is more code and more state than a hypothetical 2PC across parties. But 2PC across external parties is impossible. State the constraint and the discipline the saga buys you.]

---

## Graceful Degradation

Compliance and risk pipelines fail. The regulator endpoint is down. The ML provider rate-limits you. The notification provider has an outage. FlexFund cannot lose money or violate a regulatory clock when any of these fail.

| Capability | Primary path | Fallback when External Service is unavailable |
|---|---|---|
| Regulator submission | [Reporting Worker → External Service (regulator) with idempotency key] | [Retry Queue with exponential backoff; manual operator escalation after N attempts; audit log captures every attempt] |
| ML default scoring | [Anomaly Worker → External Service (ML model)] | [Pure Vector Database similarity search; lower confidence; audit log records the fallback] |
| Credit bureau pull | [Credit Worker → External Service (credit bureau)] | [Application held in pending state; no decision until the bureau is reachable; user notified] |
| Payment processor disbursement | [Disbursement Worker with persist-intent-first key] | [Retry Queue with backoff; dead-letter after N attempts; operator review] |
| Adverse action notice delivery | [Adverse Action Worker → External Service (notification provider)] | [Retry with same idempotency key; alternate provider (postal mail) if available; audit log records every attempt and the thirty-day margin] |

**Architectural principle**: [State explicitly. Every External Service call has a retry path. Every retry preserves idempotency. Every fallback is audit-logged. The system never loses money. The system never misses a regulatory clock without an audited reason.]

---

## Foundation Preserved

Walk through the Parts 1 and 2 paths and confirm they survive:

- **Application + identity intake**: [Application Service + File Store still in place?]
- **Credit pull idempotency**: [Per-application key on the bureau call still wired?]
- **Decision persistence**: [Decision Service still writing to Relational Database with transactional outbox to audit log?]
- **Append-only audit log with hash chain**: [Still architecturally separate, role-disciplined, hash-chained?]
- **Disbursement idempotency**: [Persist-intent-first + per-disbursement key + Retry Queue + Dead-Letter Queue still wired?]
- **Ledger at strict isolation level**: [Still the system of record?]
- **Credit Engine with version pinning**: [Still composing rule + ML with pinned versions?]
- **Time-driven Statement Worker + Delinquency Worker**: [Still firing on Time, writing to File Store?]

---

## Complete End-to-End Architecture

Provide a complete architecture diagram (or detailed text description) showing:

1. All Part 1 components (still present)
2. All Part 2 additions (still present)
3. All Part 3 additions (new): Reporting Worker + regulator External Service + File Store retention tier, Anomaly Worker + ML External Service + Vector Database + Anomaly Review Queue, Dispute Service + Relational Database state machine + File Store evidence + Dispute Event Queue + per-party Notification Workers + per-party External Services, Adverse Action Worker + File Store notices + notification provider External Service
4. The connections between them

By the end, all seven building blocks (Service, Worker, Queue, Key-Value Store, File Store, Relational Database, Vector Database) and all three external entities (User, External Service, Time) should be visible in the design.

[Include diagram or detailed text walkthrough]

---

## Trade-offs Explicitly Accepted

- **[Trade-off 1]**: [What you gave up to add regulatory reporting, anomaly detection, dispute saga, and adverse action notices]
- **[Trade-off 2]**: [What you gave up]
- **[Trade-off 3]**: [What you gave up]

---

## What This Architecture Intentionally Does NOT Address

[Be honest about what is out of scope. Examples: real-time fraud blocking at swipe time, full customer self-service dispute UI with live agent handoff, multi-currency lending, secondary market loan sales, securitization pipelines, real-time regulator dashboards. The grader rewards designs that know their boundaries.]

---

## What You Would Have Done Differently in Part 1

[The capstone reflection. With Part 3 now visible, what would you have built into Part 1 from day one? Common answers: idempotency key abstraction as a library from day one, audit-log hash chain on the first decision, dispute_id reserved on the loan row at origination, per-decision rule-set-version recorded before the Credit Engine existed. State two or three concrete changes and the cost they would have saved.]

---

## Self-Graded Rubric (A / A- / B+)

**My grade**: [A / A- / B+]

**Why I assigned this grade**: [Apply the rubric from Lesson 2. Specifically check: did you name the regulator submission as an External Service (not a Service you own)? Did you give the Vector Database a real similarity-search job (not bolted on)? Did you name the saga with explicit compensation paths (not a partial pattern)? Did you defend the rationale for saga over 2PC? Did you record the four denial fields (rule-set version, model version, credit-bureau hash, triggering score)? Did you separate "sent" from "delivered" on adverse action notices? Did you preserve every Part 1 and Part 2 pattern? Did all seven building blocks earn a job by the end?]

---

## Submission

Save this document as markdown and paste the full content into the **Challenge Part 3** submission form at [systemthinkinglab.ai](https://systemthinkinglab.ai/protected/course4/challenge3.html). Parts 1 and 2 must be graded before Part 3 can be submitted. This is the capstone of Course 4 and of the four-course series. Make it count.
