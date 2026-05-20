# Challenge 4 Part 1: Technical Design Document - FlexFund MVP

**Student Name**: [Your Name]
**Submission Date**: [Date]
**Challenge**: FlexFund Fintech Lending Platform - Part 1 MVP

---

## IMPORTANT: Technology-Agnostic Design Required

This technical design document must focus on **building blocks and architectural patterns**, not specific technologies.

**Use:**
- Building block names: Service, Worker, Queue, Key-Value Store, File Store, Relational Database, Vector Database
- External entities: User, External Service, Time
- Technology-agnostic terms: idempotency key, append-only audit log, transactional outbox, isolation level, dead-letter, persist-intent-first, hash chain

**Do NOT use:**
- Specific vendor names for credit bureaus, payment processors, banks, KYC providers, or notification gateways. Use generic terms: "credit bureau External Service", "payment processor External Service", "identity verification External Service".
- Cloud vendor names: AWS, Google Cloud, Azure, or any branded product name.
- Programming languages or frameworks: Node.js, Express, Django, Rails, Postgres as a brand, MySQL, DynamoDB, Kafka.

The grader will look for pattern recognition, idempotency discipline, and clear audit-log reasoning, not technology brand recall. Course 4 is about correctness under failure. The blocks are the same. The discipline is what changes.

## Recommended approach

1. **Draw your architecture diagram** using the 7 building blocks + 3 external entities. Use [this Google Drawing template](https://docs.google.com/drawings/d/1hbx9r8NCBNjMDZv9tAXzfvLR3-XPsOgHm9zrX0h_cO8/edit?usp=sharing) to get started.
2. **Use your diagram as reference** while writing your flows and technical explanations.
3. **Ensure consistency** between what you draw and what you write. A diagram that contradicts the prose loses points twice.

---

## Scenario

FlexFund is a consumer lending startup launching its MVP. Customers apply for a small loan from their phone. The platform pulls a credit report, decides to approve or decline, disburses funds to the borrower's bank, and tracks repayments on a ledger. You are the lead architect. The compliance officer is two weeks behind the engineering team and will read every audit-log decision you make. A double disbursement is not a UX bug, it is a regulatory event. A duplicate credit pull costs the company money and frustrates the applicant. Every decision must be auditable, with the inputs that produced it.

You are launching in one state with a single loan product. A few hundred applications per day. The Part 1 design must survive Part 2 (compliance expansion) and Part 3 (multi-state risk and reporting) without a rewrite.

---

## Architecture Overview

**High-Level Description**:
[Provide a 2-3 sentence overview of your MVP architecture. Name the application intake path, the credit decision pipeline, the disbursement pipeline, and how the audit log is wired in from day one.]

**Core Building Blocks Used** (check all that apply):
- [ ] Service (Blue Rectangle)
- [ ] Worker (Blue Trapezoid)
- [ ] Key-Value Store (Pink Diamond)
- [ ] File Store (Pink Pentagon)
- [ ] Queue (Pink Stacked Rectangles)
- [ ] Relational Database (Pink Cylinder)
- [ ] Vector Database (Pink Cube)
- [ ] User (Green Smiley)
- [ ] External Service (Green Cloud)
- [ ] Time (Green Hourglass)

Note: Vector Database is not expected in Part 1. If you check it, the grader will look for a real similarity-search use case. Anomaly detection arrives in Part 3.

---

## Requirement 1: Loan Application + Identity Verification

*A borrower submits an application through a Service. The application captures applicant details, identity documents, and consent. Identity documents are binary blobs and belong in a File Store. The structured application data belongs in a Relational Database.*

### User Flow Design

**Building block requirements:**
- Use EXACT building block names
- Use `+` for combinations (e.g., Service + File Store)
- The User always connects to a Service first, never directly to storage

```
Example formats:
Application submit: User → Application Service → Relational Database (application row)
Document upload: User → Application Service → File Store (identity document)
Document index: Application Service → Relational Database (file pointer)
```

**Your application and identity flows:**
[Write 3-5 specific flows showing the structured application write, the identity-document upload path, and how the two are linked so the audit log can later cite "the document that produced this decision".]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Why a File Store for identity documents rather than storing the bytes in the Relational Database?]
- **[Decision 2]**: [Why a Relational Database for the structured application instead of a Key-Value Store? What ACID property does the application row need?]
- **[Decision 3]**: [Is identity verification handled inline on the Application Service, or pushed to a Queue + Worker calling an identity verification External Service? Defend your choice.]

### Technical Implementation Details

**Application row shape**: [What columns matter for an audit-defensible application row? Name the immutable fields and the mutable fields, if any.]

**Document storage contract**: [What does the File Store key look like? How is the document tied back to the application ID?]

**Consent capture**: [Where does the consent record live, and what makes it tamper-evident? Is consent itself an audit-log event?]

---

## Requirement 2: Credit Decision via External Service

*The platform calls a credit bureau External Service to pull a credit report. The bureau charges per pull and the result must be deterministic for the same application. The credit pull must not block the user's request thread. The network can drop on the response, so idempotency is not optional.*

### User Flow Design

```
Example formats:
Credit pull enqueue: Application Service → Credit Pull Queue
Credit pull: Credit Pull Queue → Credit Worker → External Service (credit bureau) → Relational Database (credit result)
Decision: Credit result available → Decision Service → Relational Database (decision row)
```

**Your credit decision flows:**
[Write 3-5 specific flows showing how the credit pull is enqueued, how the Worker calls the External Service with an idempotency key, how the result is persisted, and how the decision is made.]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Why a Queue + Worker between intake and the credit bureau External Service rather than a synchronous call from the Application Service? What latency or cost penalty would the synchronous path incur?]
- **[Decision 2]**: [Name the idempotency key strategy on the credit pull. Per-application UUID, per-(applicant, day), or something else? Defend the shape.]
- **[Decision 3]**: [What happens when the credit bureau returns a 200 but the network drops before the response reaches the platform? Who retries, and with what key?]

### Technical Implementation Details

**Idempotency key strategy**: [Name the concrete key shape and why. The grader is looking for "per-application UUID" or an equally defensible commitment, not "we use idempotency".]

**Worker behavior**: [How does the Credit Worker handle a bureau timeout? Where does it record that an attempt was made before the network response arrived?]

**Persistence of bureau response**: [Is the raw bureau response stored verbatim, or is a hash of it stored? What does an auditor need to reconstruct the decision two years from now?]

---

## Requirement 3: Approval Persistence + Audit Log

*Every decision (approve, decline, refer for manual review) is persisted to the Relational Database with an audit entry. The audit entry captures the inputs that produced the decision and the output. An audit entry stored on the same row as the mutable decision is not an audit log.*

### User Flow Design

```
Example formats:
Decision write: Decision Service → Relational Database (decision row + audit row in one transaction)
Audit propagation: Relational Database (audit outbox) → Audit Worker → downstream consumers
Audit read: Compliance officer → Audit Service → Relational Database (audit table, read-only)
```

**Your approval persistence and audit flows:**
[Write 3-5 specific flows showing the decision write, the simultaneous audit write, and the path the audit row takes to any downstream consumers.]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Where does the audit log live? A separate table in the same Relational Database with INSERT-only privileges? A separate Relational Database entirely? Defend the boundary.]
- **[Decision 2]**: [Name the mechanism that prevents the application from editing the audit log after the fact. Database role privileges, an append-only constraint, or both?]
- **[Decision 3]**: [Are the decision row and the audit row written in the same database transaction? If yes, why? If no, how do you handle the case where the decision commits but the audit row never lands?]

### Technical Implementation Details

**Audit row shape**: [What columns does an audit row carry? At minimum: timestamp, actor, action, input hash, output, and the immutable identifier that links back to the decision.]

**Append-only enforcement**: [Name the concrete mechanism. The grader is looking for the words "append-only" or its functional equivalent.]

**Transactional boundary**: [If the audit row write is in the same transaction as the decision write, this is the transactional outbox pattern. Name it explicitly.]

---

## Requirement 4: Disbursement Idempotency

*The platform calls a payment processor External Service to send funds to the borrower's bank. A retry must never produce a double disbursement. Idempotency here is not a nice-to-have. A duplicate is a regulatory event.*

### User Flow Design

```
Example formats:
Disbursement enqueue: Decision Service (approved) → Disbursement Queue (with persisted intent row)
Disbursement: Disbursement Queue → Disbursement Worker → External Service (payment processor) → Relational Database (disbursement outcome)
Retry: Disbursement Worker → backoff → External Service (same idempotency key) → outcome
```

**Your disbursement flows:**
[Write 3-5 specific flows showing how the disbursement intent is persisted before the first call, how the Worker calls the payment processor, how a retry reuses the same key, and what happens on a network timeout.]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Name the idempotency key strategy on the disbursement. Per-loan-per-disbursement key, per-(loan, attempt) key, or something else?]
- **[Decision 2]**: [Why a Worker rather than the user's request thread? What is the worst case if a synchronous disbursement call hangs?]
- **[Decision 3]**: [What does the Worker do when the payment processor returns 5xx after the funds have already moved? How does the audit log protect against double-counting?]

### Technical Implementation Details

**The four properties of an idempotency key**: A senior-grade answer names all four. Commit to each one below.

- **TTL**: [The payment processor evicts keys after roughly twenty-four hours. What does your design do for a retry that fires after the TTL has expired? Does the Worker generate a fresh key, or does it consult your own Relational Database for the original outcome?]
- **Payload mismatch**: [What does the processor return when the same key arrives with a different amount? Your design must surface a 409 or equivalent, not silently return the old result.]
- **Persist-intent-first**: [Name the rule. Write the intent row and the key to your own Relational Database in a single transaction BEFORE calling the processor. State why this rule prevents a Worker crash mid-call from causing a lost disbursement.]
- **Time-fired retries**: [The key strategy applies to scheduled disbursements too. If Part 2 introduces a Time-fired retry, the same key must still be in scope. Name the boundary.]

**Idempotency key shape**: [Commit to a concrete shape. Example: `disbursement:{loan_id}:{disbursement_id}` where `disbursement_id` is a per-disbursement UUID generated at intent-persist time.]

**Worker retry policy**: [What backoff does the Worker use on a 5xx? What is the cap before the disbursement moves to a dead-letter destination? Note: Part 2 formalizes the dead-letter Queue; Part 1 just needs an immediate retry.]

---

## Requirement 5: Loan Ledger Integrity

*Principal, accrued interest, and the payment schedule live in a Relational Database as the system of record. Every state change commits at a strict isolation level. Every state change produces an audit entry. The ledger has to exist and be defensible from day one. Part 2 adds the billing clock on top of it.*

### User Flow Design

```
Example formats:
Ledger initialization: Disbursement Worker (success) → Relational Database (ledger row: principal, schedule, interest)
Ledger read: User → Ledger Service → Relational Database (current balance + schedule)
Ledger write: Repayment event → Ledger Service → Relational Database (ledger update + audit entry, one transaction)
```

**Your ledger flows:**
[Write 3-5 specific flows for ledger initialization, ledger reads, and ledger writes. Be explicit about which writes commit in the same transaction as their audit entries.]

### Architecture Decisions & Trade-offs

**Key architectural decisions:**
- **[Decision 1]**: [Why a Relational Database for the ledger rather than a Key-Value Store or a File Store? What ACID property does the ledger require?]
- **[Decision 2]**: [Name the ACID isolation level the ledger runs at. Read committed, repeatable read, snapshot, or serializable? Why?]
- **[Decision 3]**: [Why is every ledger state change paired with an audit entry in the same transaction? What goes wrong if they commit independently?]

### Technical Implementation Details

**Ledger row shape**: [What columns matter on a ledger row? Principal, accrued interest, last-payment date, schedule pointer, status. Anything else?]

**Isolation level commitment**: [Name the level. State the trade-off you accepted: stronger isolation costs throughput; weaker isolation risks anomaly. Defend your choice for a lending ledger.]

**Audit linkage**: [Every ledger update writes an audit entry that names the actor (Worker, user, scheduled job), the before state, the after state, and the inputs. Confirm your design does this.]

---

## Overall Architecture Analysis

### Key design decisions (whole-system level)

1. **[Decision 1]**: [Rationale]
2. **[Decision 2]**: [Rationale]
3. **[Decision 3]**: [Rationale]

### Building block combinations used

- **[Pattern 1]**: [Which building blocks combined, where, and why. Example: Queue + Worker + External Service for asynchronous credit pull with idempotency.]
- **[Pattern 2]**: [Which building blocks combined, where, and why. Example: Relational Database (decision row) + Relational Database (audit table) in the same transaction for the transactional outbox.]
- **[Pattern 3]**: [Which building blocks combined, where, and why. Example: Worker + External Service + Relational Database (intent row) for persist-intent-first disbursement.]

### Trade-offs explicitly accepted

- **[Trade-off 1]**: [What you gave up and what you gained. Example: added latency from the Queue + Worker on the credit path in exchange for retry safety and idempotency discipline.]
- **[Trade-off 2]**: [What you gave up and what you gained. Example: stronger isolation level on the ledger in exchange for guaranteed correctness on every dollar moved.]
- **[Trade-off 3]**: [What you gave up and what you gained.]

### What this MVP intentionally does NOT address

[Anything you are deferring to Part 2 or Part 3. Be explicit. Examples: immutable hash-chained audit log, retry pipeline with exponential backoff and dead-letter, Time-driven statement and delinquency Workers, ML credit scoring, regulatory reporting, anomaly detection with Vector Database, dispute saga, adverse action notices. The grader rewards designs that know their boundaries.]

### Self-graded rubric (A / A- / B+)

**My grade**: [A / A- / B+]

**Why I assigned this grade**: [One paragraph. A means all five requirements + concrete idempotency key strategies on both the credit pull and disbursement + audit log architecturally separate + ACID acknowledged + the four idempotency properties named for the disbursement. A- means strong with one precision gap. B+ means solid but missing one of the named properties or a hand-waved key strategy.]

---

## Submission

Save this document as markdown and paste the full content into the **Challenge Part 1** submission form at [systemthinkinglab.ai](https://systemthinkinglab.ai/protected/course4/challenge1.html). You will receive AI-graded feedback within 24 hours.
