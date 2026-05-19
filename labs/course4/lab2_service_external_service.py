#!/usr/bin/env python3
# =============================================================================
# Systems Thinking in the AI Era
# https://systemthinkinglab.ai
#
# This code is part of the "Systems Thinking in the AI Era" course series.
# For more information, educational content, and courses, visit:
# https://systemthinkinglab.ai
# =============================================================================

"""
Systems Thinking in the AI Era IV: Business & Transaction Systems
Lab 2: Service + External Service — Payment Integration Discovery
Interactive Python Application

Three progressive experiments that build intuition for the failure modes
of integrating with an External Service over the network.

  1. Sync vs Queue+Worker      — what does the user wait for?
  2. Timeout + idempotency      — same retry, with and without a key
  3. Webhook security           — HMAC signature plus a Time replay window

After each experiment, three reflection questions with immediate educational
feedback. Wrong answers teach as much as right ones.
"""

import os
import sys
import time
import hmac
import hashlib
import random
import argparse
import threading
import uuid
from typing import Optional, List, Dict

# Dual-mode import so this file works in both layouts:
#   1. Monorepo / standalone:  building_blocks.py sits next to this file (sibling import)
#   2. course4-supplement repo: building_blocks/ is a top-level package
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(script_dir)))

try:
    from building_blocks import Service, Worker, Queue
    from external_entities import ExternalService
except ImportError:
    try:
        from building_blocks.building_blocks import Service, Worker, Queue
        from building_blocks.external_entities import ExternalService
    except ImportError:
        print("Error: Could not import building_blocks / external_entities modules.")
        print("Expected files next to this lab, OR building_blocks/ package at repo root.")
        sys.exit(1)


# =============================================================================
# Lab Experience
# =============================================================================

class LabExperience:
    """Interactive lab for Course IV, Lab 2: Service + External Service."""

    def __init__(self, student_name: str = "Student"):
        self.student_name = student_name
        self.experiment_times: Dict[str, float] = {}
        self.correct_answers = 0
        self.total_questions = 0

        self.separator = "=" * 80
        self.mini_separator = "-" * 40

        self.typewriter_speed = 0.03
        self.fast_typewriter_speed = 0.01
        self.instant_print = False

        self.print_lock = threading.Lock()

    # -----------------------------------------------------------------------
    # Print helpers
    # -----------------------------------------------------------------------

    def typewriter_print(self, text: str, speed: Optional[float] = None, end: str = "\n"):
        if self.instant_print:
            print(text, end=end)
            return
        if speed is None:
            speed = self.typewriter_speed
        for char in text:
            print(char, end='', flush=True)
            if char not in [' ', '\n', '\t']:
                time.sleep(speed)
        print(end=end)

    def direct_print(self, text: str, end: str = "\n"):
        with self.print_lock:
            print(text, end=end)

    def print_header(self, text: str, style: str = "main"):
        if style == "main":
            print(f"\n{self.separator}")
            print(f"🎯 {text.upper()}")
            print(self.separator)
        elif style == "sub":
            print(f"\n{self.mini_separator}")
            print(f"▶️  {text}")
            print(self.mini_separator)
        elif style == "experiment":
            print(f"\n{'🧪' * 20}")
            print(f"🧪 EXPERIMENT: {text}")
            print('🧪' * 20)

    def print_experiment(self, text: str):
        self.print_header(text, style="experiment")

    def print_info(self, text: str, indent: int = 0):
        prefix = "  " * indent + "ℹ️ " if indent == 0 else "  " * indent
        for line in text.strip().split('\n'):
            self.typewriter_print(f"{prefix}{line}")

    def print_action(self, text: str):
        self.typewriter_print(f"⚡ {text}", speed=self.fast_typewriter_speed)

    def print_result(self, text: str):
        self.typewriter_print(f"✅ {text}")

    def print_warning(self, text: str):
        self.typewriter_print(f"⚠️  {text}")

    def wait_for_enter(self, prompt: str = "Press ENTER to continue..."):
        input(f"\n📍 {prompt}")

    def ask_yes_no(self, question: str) -> bool:
        while True:
            response = input(f"\n❓ {question} (yes/no): ").lower().strip()
            if response in ['yes', 'y']:
                return True
            if response in ['no', 'n']:
                return False
            print("Please answer 'yes' or 'no'")

    def ask_multiple_choice(self, question: str, choices: List[str],
                            responses: List[str], correct_index: int = 0) -> str:
        self.total_questions += 1

        print(f"\n💭 REFLECTION QUESTION:")
        print(f"   {question}\n")
        for i, choice in enumerate(choices, 1):
            print(f"   {i}. {choice}")

        while True:
            try:
                choice_input = input(f"\n❓ Enter your choice (1-{len(choices)}): ").strip()
                choice_num = int(choice_input)
                if 1 <= choice_num <= len(choices):
                    break
                print(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print(f"Please enter a valid number between 1 and {len(choices)}")

        selected_choice = choices[choice_num - 1]
        educational_response = responses[choice_num - 1]

        if choice_num - 1 == correct_index:
            self.correct_answers += 1
            print(f"\n✅ You selected: {selected_choice}")
        else:
            print(f"\n📘 You selected: {selected_choice}")

        print("\n🎯 ", end='')
        self.typewriter_print(educational_response)
        self.wait_for_enter()
        return selected_choice

    # -----------------------------------------------------------------------
    # Welcome
    # -----------------------------------------------------------------------

    def run_welcome(self):
        self.print_header("WELCOME TO SYSTEMS THINKING IN THE AI ERA")
        print("\n🎓 Systems Thinking in the AI Era IV: Business & Transaction Systems")
        print("📚 Lab 2: Service + External Service — Payment Integration Discovery\n")

        self.typewriter_print("Transform from an engineer who calls a payment API")
        self.typewriter_print("to an architect who knows what each failure mode costs.")

        self.student_name = input("\n\n👤 What's your name? ").strip() or "Student"
        self.typewriter_print(f"\nWelcome, {self.student_name}! Let's break some payment flows.")

        self.print_info("""
You're about to feel, not just read about, why every production payment
integration carries idempotency keys, signed webhooks, and a deduplication
window. Each pattern earns its keep by failing safely under a specific
breakage you'll watch happen.

You'll run three experiments:
1. Sync payment call vs Queue + Worker — who is waiting on whom?
2. Idempotency keys on a timeout — what happens to the second tap on Pay?
3. Webhook signature + replay window — both attackers and retries get caught.

After each experiment you'll answer three reflection questions with
immediate educational feedback. Wrong answers teach as much as right ones.
""")
        self.wait_for_enter("Ready to discover? Press ENTER to begin!")

    # =======================================================================
    # EXPERIMENT 1: Sync vs Queue+Worker
    # =======================================================================

    def experiment_1_sync_vs_queue(self):
        self.print_experiment("Sync Payment vs Queue + Worker")

        self.print_info("""
The user clicks Pay. Two designs:

  PATH A: The Web Service synchronously calls the payment processor
          External Service. The user waits until the processor responds.

  PATH B: The Web Service writes the order to a Queue and returns
          immediately. A Worker drains the Queue, calls the processor,
          and updates the order asynchronously.

You'll run ten payments through each path and compare the user-facing
latency. The work is the same; only the boundary changes.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # The External Service runs slowly on purpose so the difference shows
        processor = ExternalService("payment_processor")
        processor.set_reliability(failure_rate=0.0, latency_range=(0.30, 0.40))

        # -------------------------------------------------------------------
        # PART A: Synchronous Service-to-ExternalService call
        # -------------------------------------------------------------------
        self.print_header("Part A: Synchronous Call to Payment Processor", style="sub")

        sync_service = Service("checkout_sync")

        @sync_service.route("/checkout")
        def sync_checkout(data):
            # The Service makes a synchronous call to the External Service.
            # The user's request thread is blocked the entire time.
            response = processor.make_request(
                endpoint="/charge",
                method="POST",
                data={"amount": data["amount"], "currency": "usd"}
            )
            return {"status": "charged", "processor_response_time": response.get("response_time")}

        self.print_action("Running 10 checkouts through the synchronous Service...")
        sync_latencies = []
        for i in range(10):
            t0 = time.perf_counter()
            sync_service.handle_request("/checkout", data={"amount": 50})
            sync_latencies.append((time.perf_counter() - t0) * 1000)

        avg_sync = sum(sync_latencies) / len(sync_latencies)
        self.direct_print(f"   Sync user-facing latency: avg {avg_sync:.0f}ms per checkout")
        self.print_warning(
            "The user waits for the processor on every call. If the processor "
            "is slow, the user's spinner keeps spinning. If the processor is "
            "down, the user's checkout fails."
        )

        # -------------------------------------------------------------------
        # PART B: Queue + Worker handles the External Service call
        # -------------------------------------------------------------------
        self.print_header("Part B: Queue + Worker (Async)", style="sub")

        payment_queue = Queue("payment_queue")
        processed_orders: List[Dict] = []
        processed_lock = threading.Lock()

        @payment_queue.subscriber("payment_request")
        def payment_worker(message):
            # The Worker (subscriber drain) calls the External Service. The
            # user is long gone by the time this runs.
            response = processor.make_request(
                endpoint="/charge",
                method="POST",
                data={"amount": message["amount"], "currency": "usd"}
            )
            with processed_lock:
                processed_orders.append({
                    "order_id": message["order_id"],
                    "processor_status": response.get("status"),
                })

        time.sleep(0.1)  # let the subscriber register cleanly

        async_service = Service("checkout_async")

        @async_service.route("/checkout")
        def async_checkout(data):
            # Service writes the order to the Queue and returns 202 Accepted.
            # No external call on the request thread.
            order_id = str(uuid.uuid4())
            payment_queue.enqueue(
                {"order_id": order_id, "amount": data["amount"]},
                message_type="payment_request"
            )
            return {"status": "accepted", "order_id": order_id}

        self.print_action("Running 10 checkouts through the Queue + Worker design...")
        async_latencies = []
        for i in range(10):
            t0 = time.perf_counter()
            async_service.handle_request("/checkout", data={"amount": 50})
            async_latencies.append((time.perf_counter() - t0) * 1000)

        avg_async = sum(async_latencies) / len(async_latencies)
        self.direct_print(f"   Async user-facing latency: avg {avg_async:.1f}ms per checkout")

        # Wait for the Worker to drain the Queue
        self.print_action("Waiting for the Worker to drain the Queue...")
        deadline = time.perf_counter() + 8.0
        while time.perf_counter() < deadline:
            with processed_lock:
                if len(processed_orders) >= 10:
                    break
            time.sleep(0.1)

        self.direct_print(f"   Processed by Worker: {len(processed_orders)}/10 orders")
        self.print_result(
            f"Sync: {avg_sync:.0f}ms blocking the user. "
            f"Async: {avg_async:.1f}ms returning to the user. "
            f"User waits ~{avg_sync / max(avg_async, 0.1):.0f}x less in the async design."
        )
        self.print_info("""
Same External Service work, same per-call latency, completely different
user experience. The Queue moved the slow call off the request path.

This is the pattern under every checkout that returns "Order received,
we are processing your payment" instantly: a Service plus Queue plus
Worker plus External Service.
""")

        payment_queue.stop()
        self.experiment_times['experiment_1'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 1 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why did the async design return so much faster to the user?",
            [
                "Because the Service's response was decoupled from the External Service call. The Service only wrote to the Queue and returned; the Worker called the processor later.",
                "Because the Queue made the processor faster.",
                "Because async requests skip the External Service entirely.",
            ],
            [
                "Exactly. The Queue is the seam that moves the External Service work off the request path. The processor still takes the same 300-400ms on every call — that work hasn't gone away. The user just isn't waiting for it. The Worker is the one waiting, and the Worker has no spinner to spin.",
                "The processor's latency is unchanged. The processor does the same 300-400ms of work whether it is called by a Service handling a user request or by a Worker draining a Queue. The Queue did not speed the processor up; it shifted who is blocked by it.",
                "Async does not skip the External Service. The processor still gets called once per order, with the same payload, and produces the same outcome. The Worker is the one making the call now. The user just no longer has to be present for it.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "What new failure mode does the Queue + Worker design introduce that the sync design did not have?",
            [
                "The user does not learn synchronously whether the charge succeeded. The Service needs another channel (webhook, polling, async notification) to tell the user once the Worker finishes.",
                "Queue + Worker designs cannot retry failed payments.",
                "The Queue corrupts payments if the Worker is slow.",
            ],
            [
                "Right. The trade-off is exactly that: synchronous designs give the user the answer in line with the request. Async designs do not. The architecture has to compensate with a notification path (webhook update, websocket push, email, in-app polling) so the user finds out the charge succeeded — or failed. The Queue+Worker pattern is incomplete without that update path.",
                "Queue + Worker is the BEST shape for retries. The Worker can replay a failed call with backoff, route to a dead-letter Queue after N attempts, and the user is not involved in any of that. The sync design has fewer retry options because the user is waiting.",
                "Queues do not corrupt payments. A slow Worker simply means messages back up in the Queue. The payments themselves are unaffected. Backpressure (a bounded Queue + monitoring) is the production answer to a slow Worker — not corruption.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "When would you choose the synchronous design over the async one?",
            [
                "When the user genuinely needs to know the outcome before the page transitions, AND the External Service is fast and reliable enough to make waiting tolerable.",
                "Whenever payments are involved. Money math should never be async.",
                "Never. Async is always better.",
            ],
            [
                "Exactly. The decision is product, not just engineering. A checkout that must show 'thank you' immediately needs the sync answer. A high-volume webhook ingestion pipeline needs the async path. Some flows even do both: sync best-effort with a fast timeout, then fall through to the Queue for the slow case. A senior engineer names the trade and picks the right shape per flow.",
                "Plenty of money flows are async. Bank transfers, ACH, settlement reconciliation, payout runs — all of these are asynchronous by design. The 'sync feels safer' instinct is correct for the user-facing checkout, but not for every money operation. The choice depends on who needs the answer when.",
                "Async is not always better. Adding a Queue + Worker pair brings operational cost: a Queue to monitor, a Worker to scale, a dead-letter Queue to triage. For a low-volume flow with a fast, reliable External Service, sync is simpler and the right choice. The engineer's job is to pick.",
            ],
            correct_index=0,
        )

    # =======================================================================
    # EXPERIMENT 2: Idempotency on Timeout
    # =======================================================================

    def experiment_2_idempotency_on_timeout(self):
        self.print_experiment("Idempotency on a Timeout")

        self.print_info("""
The customer clicks Pay. The Service calls the payment processor. The
processor processes the charge — but the response gets lost on the
network on the way back. The Service surfaces a timeout. The customer,
seeing a spinner then an error, clicks Pay again.

Two paths:

  PATH A: The Service does NOT send an idempotency key. The processor
          treats the second call as a brand-new intent. The customer
          is charged twice.

  PATH B: The Service generates ONE idempotency key per click-intent
          and reuses it on retry. The processor recognizes the key
          and returns the original result. The customer is charged once.

You'll watch each path. The difference is one HTTP header.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # We'll simulate the processor as a stateful Service that knows about
        # idempotency keys. It records every charge it accepts, and on a
        # repeat key it returns the prior result instead of re-charging.

        # processor_ledger maps idempotency_key -> charge_id
        processor_ledger: Dict[str, str] = {}
        processor_charges: List[Dict] = []
        ledger_lock = threading.Lock()

        def processor_charge(amount: int, idempotency_key: Optional[str] = None) -> Dict:
            """Simulated processor with optional idempotency.

            If idempotency_key is provided and seen before, replay the result.
            Otherwise, create a new charge.
            """
            # The processor itself is fast — 50ms — but we simulate the
            # network drop on the response. So from the Service's point
            # of view, the call timed out. From the processor's point of
            # view, the charge happened.
            time.sleep(0.05)
            with ledger_lock:
                if idempotency_key and idempotency_key in processor_ledger:
                    charge_id = processor_ledger[idempotency_key]
                    return {"charge_id": charge_id, "amount": amount, "replayed": True}
                charge_id = "ch_" + uuid.uuid4().hex[:10]
                processor_charges.append(
                    {"charge_id": charge_id, "amount": amount,
                     "idempotency_key": idempotency_key}
                )
                if idempotency_key:
                    processor_ledger[idempotency_key] = charge_id
                return {"charge_id": charge_id, "amount": amount, "replayed": False}

        def lose_response_on_the_way_back(actual_result: Dict) -> Dict:
            """The processor processed the charge, but the response never
            made it back to the Service. We model this as the Service
            seeing a timeout error, while the processor's ledger has the
            new charge."""
            return {"error": "timeout", "actual_processor_state": actual_result}

        # -------------------------------------------------------------------
        # PART A: No idempotency key → retry double-charges
        # -------------------------------------------------------------------
        self.print_header("Part A: Retry With No Idempotency Key", style="sub")

        def first_call_no_key(amount: int):
            # First call: processor records the charge, response is "lost"
            actual = processor_charge(amount=amount)
            return lose_response_on_the_way_back(actual)

        def retry_no_key(amount: int):
            # Retry: processor has no key to match on, records a brand-new charge
            return processor_charge(amount=amount)

        self.print_action("Customer clicks Pay for $99. Processor receives the call.")
        first_result = first_call_no_key(amount=99)
        self.direct_print(f"   Service saw: {first_result['error']}")
        self.direct_print(
            f"   Processor's real state: charge {first_result['actual_processor_state']['charge_id']} "
            f"for ${first_result['actual_processor_state']['amount']}"
        )

        self.print_action("Customer sees the error and taps Pay again.")
        retry_result = retry_no_key(amount=99)
        self.direct_print(
            f"   Processor responded: charge {retry_result['charge_id']} for ${retry_result['amount']}"
        )

        self.direct_print(f"\n   Total charges in processor ledger: {len(processor_charges)}")
        for c in processor_charges:
            self.direct_print(
                f"     {c['charge_id']} ${c['amount']} (key={c['idempotency_key'] or 'none'})"
            )

        self.print_warning(
            "Two charges. Customer was charged $99 twice. The processor had no "
            "way to know the retry was for the same intent. The Service did not "
            "send a key to deduplicate on."
        )

        # -------------------------------------------------------------------
        # PART B: Same scenario, with one idempotency key per click-intent
        # -------------------------------------------------------------------
        self.print_header("Part B: Retry With the SAME Idempotency Key", style="sub")

        # Reset the processor ledger
        with ledger_lock:
            processor_ledger.clear()
            processor_charges.clear()

        # The Service generates ONE key per click-intent. Both the first
        # call and the retry carry the same key.
        intent_key = "ip_" + uuid.uuid4().hex[:10]
        self.print_action(f"Customer clicks Pay for $99. Service generates idempotency key: {intent_key}")

        first_actual = processor_charge(amount=99, idempotency_key=intent_key)
        first_lost = lose_response_on_the_way_back(first_actual)
        self.direct_print(f"   Service saw: {first_lost['error']}")
        self.direct_print(
            f"   Processor's real state: charge {first_actual['charge_id']} "
            f"for ${first_actual['amount']} (key={intent_key})"
        )

        self.print_action("Customer taps Pay again. The Service retries with the SAME key.")
        retry_actual = processor_charge(amount=99, idempotency_key=intent_key)
        self.direct_print(
            f"   Processor responded: charge {retry_actual['charge_id']} for "
            f"${retry_actual['amount']} (replayed={retry_actual['replayed']})"
        )

        self.direct_print(f"\n   Total charges in processor ledger: {len(processor_charges)}")
        for c in processor_charges:
            self.direct_print(
                f"     {c['charge_id']} ${c['amount']} (key={c['idempotency_key']})"
            )

        self.print_result(
            "One charge. The processor recognized the key on the retry and "
            "returned the original result. Customer charged once. The retry "
            "was safe because the Service held the key constant across attempts."
        )

        # -------------------------------------------------------------------
        # PART C: Payload mismatch on the same key — the 409 path
        # -------------------------------------------------------------------
        self.print_header("Part C: Same Key, Different Amount — 409 Conflict", style="sub")

        self.print_info("""
A buggy client reuses an idempotency key but changes the request body
(amount, currency, recipient). Production payment APIs hash the payload
and refuse this with a 409 conflict. Mirror that behavior in our processor.
""")

        def processor_charge_strict(amount: int, idempotency_key: str) -> Dict:
            with ledger_lock:
                if idempotency_key in processor_ledger:
                    prior_id = processor_ledger[idempotency_key]
                    # Find the prior charge to check the payload
                    prior = next(
                        (c for c in processor_charges if c["charge_id"] == prior_id),
                        None
                    )
                    if prior and prior["amount"] != amount:
                        return {
                            "error": "idempotency_key_payload_mismatch",
                            "status": 409,
                            "message": (
                                f"Key {idempotency_key} previously used with "
                                f"amount=${prior['amount']}. Refusing replay at "
                                f"amount=${amount}."
                            ),
                        }
                    return {"charge_id": prior_id, "amount": amount, "replayed": True}
                charge_id = "ch_" + uuid.uuid4().hex[:10]
                processor_charges.append(
                    {"charge_id": charge_id, "amount": amount,
                     "idempotency_key": idempotency_key}
                )
                processor_ledger[idempotency_key] = charge_id
                return {"charge_id": charge_id, "amount": amount, "replayed": False}

        # Reset
        with ledger_lock:
            processor_ledger.clear()
            processor_charges.clear()

        buggy_key = "ip_" + uuid.uuid4().hex[:10]
        self.print_action(f"First call: $99 with key {buggy_key}")
        r1 = processor_charge_strict(amount=99, idempotency_key=buggy_key)
        self.direct_print(f"   Processor: charge {r1['charge_id']} for ${r1['amount']}")

        self.print_action("Second call: same key but the amount is $990 (bug!).")
        r2 = processor_charge_strict(amount=990, idempotency_key=buggy_key)
        self.direct_print(f"   Processor: {r2}")

        self.print_result(
            "The processor refused the replay because the payload changed. "
            "This is the 409 contract: same key implies same intent. The "
            "moment the payload disagrees, the provider stops you. Treat 409 "
            "as a real bug to fix in your code, not a retry signal."
        )

        self.experiment_times['experiment_2'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 2 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "In Part A, the processor really did process the first charge — but the Service saw a timeout. What is the architectural lesson?",
            [
                "A timeout on the Service side does not mean the External Service did not do the work. The two sides can disagree about whether the call succeeded.",
                "The processor was misconfigured. A correct processor would have rolled back the charge when the response failed.",
                "Timeouts are always the network's fault and never the application's responsibility.",
            ],
            [
                "Exactly. This is the foundational ambiguity that idempotency keys exist to handle. From the Service's perspective, the call may have succeeded or failed — there is no way to tell from a timeout alone. The next call has to be safe to assume EITHER outcome. The only safe assumption is that the work might have happened, and the key lets the External Service confirm yes-or-no on the retry.",
                "Processors do not roll back charges on response-side network failures. They cannot — they only see their side of the wire. The charge was processed successfully on their end; the response was lost in transit. This is exactly why retries exist: to let the client confirm what the server already knows.",
                "The application is fully responsible for handling this ambiguity. The network is the medium, not an actor that can be blamed. Architecture that ignores timeout ambiguity ships double-charges to production. The senior-engineer response is to design for it from day one with idempotency keys.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "The key in Part B is described as 'one per click-intent.' Why not generate a new key on each retry?",
            [
                "Because the key is the deduplication handle. If every retry has a fresh key, the processor cannot recognize them as related, and every retry creates a new charge.",
                "Because the processor caches keys and rejects rapid-fire fresh ones.",
                "Because keys are expensive to generate.",
            ],
            [
                "Exactly. The key represents the intent ('this user wants to pay $99 for order X'), not the attempt. All retries of the same intent must carry the same key. Generating a new key on retry is functionally identical to having no key at all — the processor cannot dedup. A senior engineer generates the key BEFORE the first call, persists it (often in the Relational Database alongside the order), and reuses it on every retry.",
                "Processors do not throttle on rapid fresh keys. They accept fresh keys at any rate the rate limiter allows. The problem with a fresh key is correctness, not throttling.",
                "Keys are typically UUIDs. Generation is microseconds. Cost is not the reason. The reason is that a fresh key destroys the deduplication contract.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "In Part C, the 409 fired because the payload changed. What is the right behavior in the Service?",
            [
                "Log it, page someone, and fix the bug that produced a same-key, different-payload retry. The 409 is a signal of a client-side defect, not a retry signal.",
                "Generate a fresh key and retry the new payload.",
                "Ignore the 409 and assume the original charge stuck.",
            ],
            [
                "Exactly. A 409 means your code reused a key it should not have. The right response is to surface the bug — alert, log, and trace — not to paper over it with a retry. Eventually the buggy code path needs to either A) generate a fresh key for the new intent, or B) stop reusing the key for a different request. Both are code fixes, not runtime behaviors.",
                "Generating a fresh key on a 409 might let the call go through, but it does not address the actual bug: somewhere in your code, the same key got attached to a different request. That bug will fire again. Fix the cause, not the symptom.",
                "You CAN look up the original charge to confirm it stuck, but that does not address the bug that produced the mismatch. The 409 is the provider telling you 'your client has inconsistent state.' Investigate it.",
            ],
            correct_index=0,
        )

    # =======================================================================
    # EXPERIMENT 3: Webhook Signature + Replay Window
    # =======================================================================

    def experiment_3_webhook_signature_and_replay(self):
        self.print_experiment("Webhook Signature Verification and Replay Protection")

        self.print_info("""
The payment processor calls YOUR Service when something changes on
their side: a charge settled, a customer disputed, a payment refunded.
This is a webhook.

Webhooks are inbound calls from outside your trust boundary. Two
attacks fail when your Service is naive:

  ATTACK 1: An adversary sends a forged webhook that looks like the
            processor's payload. Without an HMAC signature check, your
            Service accepts it and updates state.

  ATTACK 2: An adversary captures a legitimate webhook and replays it
            later. Without a deduplication window, your Service
            processes the same event twice.

You'll watch both attacks succeed against a naive Service, then watch
them fail against a Service that verifies the signature and rejects
replays.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # The processor and the Service share a webhook secret out of band.
        # In production this comes from the processor's dashboard.
        WEBHOOK_SECRET = "whsec_" + uuid.uuid4().hex

        def sign_payload(payload: str, timestamp: int) -> str:
            """Compute the HMAC-SHA256 signature the way most providers do:
            sign 'timestamp.payload' with the shared secret."""
            signed_string = f"{timestamp}.{payload}".encode("utf-8")
            return hmac.new(
                WEBHOOK_SECRET.encode("utf-8"),
                signed_string,
                hashlib.sha256,
            ).hexdigest()

        def make_processor_webhook(event_id: str, charge_id: str, status: str,
                                   timestamp: Optional[int] = None) -> Dict:
            """Build a webhook the way the processor would build it."""
            ts = timestamp if timestamp is not None else int(time.time())
            payload = f'{{"event_id":"{event_id}","charge_id":"{charge_id}","status":"{status}"}}'
            signature = sign_payload(payload, ts)
            return {
                "headers": {
                    "X-Processor-Signature": signature,
                    "X-Processor-Timestamp": str(ts),
                },
                "body": payload,
            }

        # -------------------------------------------------------------------
        # PART A: Naive Service accepts any webhook
        # -------------------------------------------------------------------
        self.print_header("Part A: Naive Webhook Receiver (No Signature Check)", style="sub")

        naive_service = Service("webhook_receiver_naive")
        naive_events_recorded: List[str] = []
        naive_lock = threading.Lock()

        @naive_service.route("/webhook")
        def naive_webhook(data):
            # No signature check, no timestamp check, no replay check.
            # Just process whatever arrives.
            with naive_lock:
                naive_events_recorded.append(data["body"])
            return {"received": True}

        # Legitimate webhook from the processor
        good_webhook = make_processor_webhook(
            event_id="evt_001", charge_id="ch_abc123", status="succeeded"
        )
        self.print_action("Processor sends a legitimate webhook for ch_abc123 succeeded.")
        naive_service.handle_request("/webhook", data=good_webhook)
        self.direct_print(f"   Events recorded: {len(naive_events_recorded)}")

        # Attacker forges a webhook with no shared secret
        forged_webhook = {
            "headers": {
                "X-Processor-Signature": "deadbeef" * 8,
                "X-Processor-Timestamp": str(int(time.time())),
            },
            "body": '{"event_id":"evt_002","charge_id":"ch_attacker","status":"succeeded"}',
        }
        self.print_action("Attacker forges a webhook claiming ch_attacker just succeeded.")
        naive_service.handle_request("/webhook", data=forged_webhook)
        self.direct_print(f"   Events recorded: {len(naive_events_recorded)}")
        self.print_warning(
            "The naive Service accepted both. The forged webhook just told the "
            "system a charge succeeded when no such charge exists. "
            "Anyone who can hit the endpoint can lie."
        )

        # Replay attack
        self.print_action("Attacker captures the legitimate good_webhook and replays it twice.")
        naive_service.handle_request("/webhook", data=good_webhook)
        naive_service.handle_request("/webhook", data=good_webhook)
        self.direct_print(f"   Events recorded: {len(naive_events_recorded)}")
        self.print_warning(
            "Same legitimate event recorded three times. If the Service "
            "credits the merchant on every 'charge.succeeded' event, the "
            "merchant just got paid 3x for one transaction."
        )

        # -------------------------------------------------------------------
        # PART B: Signature check rejects forgeries
        # -------------------------------------------------------------------
        self.print_header("Part B: Verify HMAC Signature on Inbound Webhooks", style="sub")

        safe_service = Service("webhook_receiver_safe")
        safe_events_recorded: List[str] = []
        safe_lock = threading.Lock()
        safe_event_ids_seen: set = set()
        REPLAY_WINDOW_SECONDS = 5  # tight window for the lab; production is 5 min

        @safe_service.route("/webhook")
        def safe_webhook(data):
            timestamp_str = data["headers"].get("X-Processor-Timestamp")
            signature = data["headers"].get("X-Processor-Signature")
            body = data["body"]

            # 1. Verify the signature
            if not timestamp_str or not signature:
                return {"error": "missing_signature_headers", "status": 401}
            try:
                ts = int(timestamp_str)
            except ValueError:
                return {"error": "bad_timestamp", "status": 401}
            expected = sign_payload(body, ts)
            if not hmac.compare_digest(expected, signature):
                return {"error": "invalid_signature", "status": 401}

            # 2. Verify the timestamp is within the replay window
            now = int(time.time())
            if abs(now - ts) > REPLAY_WINDOW_SECONDS:
                return {"error": "timestamp_outside_replay_window", "status": 401}

            # 3. Dedup by event_id within the window (the Service stores the
            # set of recently-seen event_ids; a real Service uses a
            # Key-Value Store with TTL)
            import json
            try:
                parsed = json.loads(body)
            except Exception:
                return {"error": "bad_payload", "status": 400}
            event_id = parsed.get("event_id")
            if not event_id:
                return {"error": "missing_event_id", "status": 400}
            with safe_lock:
                if event_id in safe_event_ids_seen:
                    return {"received": True, "deduped": True, "event_id": event_id}
                safe_event_ids_seen.add(event_id)
                safe_events_recorded.append(body)
            return {"received": True, "deduped": False, "event_id": event_id}

        # Legitimate webhook
        good_webhook2 = make_processor_webhook(
            event_id="evt_010", charge_id="ch_xyz999", status="succeeded"
        )
        self.print_action("Processor sends a legitimate webhook for ch_xyz999.")
        r = safe_service.handle_request("/webhook", data=good_webhook2)
        self.direct_print(f"   Result: {r.get('data')}")

        # Attacker forges (wrong signature)
        forged2 = {
            "headers": {
                "X-Processor-Signature": "deadbeef" * 8,
                "X-Processor-Timestamp": str(int(time.time())),
            },
            "body": '{"event_id":"evt_011","charge_id":"ch_attacker","status":"succeeded"}',
        }
        self.print_action("Attacker forges another webhook.")
        r = safe_service.handle_request("/webhook", data=forged2)
        self.direct_print(f"   Result: {r.get('data')}")
        self.print_result(
            "The signature check refused the forgery. Only the processor "
            "knows the shared secret, so only the processor can produce a "
            "signature that verifies. Forged webhooks die at the door."
        )

        # Replay of the legitimate webhook
        self.print_action("Attacker captures good_webhook2 and replays it twice.")
        r1 = safe_service.handle_request("/webhook", data=good_webhook2)
        r2 = safe_service.handle_request("/webhook", data=good_webhook2)
        self.direct_print(f"   Replay 1: {r1.get('data')}")
        self.direct_print(f"   Replay 2: {r2.get('data')}")
        self.print_result(
            "Both replays were caught — same event_id, already seen. "
            "deduped=true is the safe-no-op response. The replay window "
            "(here 5 seconds; in production five minutes) bounds the size "
            "of the seen-event set the Service has to remember."
        )

        # -------------------------------------------------------------------
        # PART C: Replay-window expiration also fails
        # -------------------------------------------------------------------
        self.print_header("Part C: Replay From Outside the Window", style="sub")

        self.print_info("""
The dedup set cannot grow forever. The replay window bounds it: events
older than the window are rejected by the timestamp check before they
even reach the dedup set. We will simulate an old webhook arriving.
""")

        # An "old" webhook with timestamp from 30 seconds ago
        old_ts = int(time.time()) - 30
        old_webhook = make_processor_webhook(
            event_id="evt_020", charge_id="ch_old", status="succeeded",
            timestamp=old_ts
        )
        self.print_action(f"Attacker replays a 30-second-old webhook (replay window is 5s).")
        r = safe_service.handle_request("/webhook", data=old_webhook)
        self.direct_print(f"   Result: {r.get('data')}")
        self.print_result(
            "Rejected at the timestamp check. The replay window pairs with "
            "the dedup set: the window keeps the set bounded, and the "
            "timestamp check is itself a defense against attackers who "
            "capture an event today and try to use it next week."
        )

        self.experiment_times['experiment_3'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 3 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "Why does the HMAC signature defeat forged webhooks?",
            [
                "Because only the processor knows the shared secret. Without the secret, an attacker cannot produce a matching HMAC, no matter what payload they craft.",
                "Because HMAC is computationally expensive, so attackers give up.",
                "Because the Service rate-limits unsigned requests.",
            ],
            [
                "Exactly. The signature is a keyed hash: HMAC(secret, timestamp + body). The verifier recomputes it with its own copy of the secret and compares. An attacker without the secret has no way to produce a signature that verifies. This is cryptographic authentication, not encryption — the payload is still readable, but its authenticity is verifiable.",
                "HMAC is fast, not slow. A modern machine computes hundreds of thousands per second. The defense is not computational cost; it is mathematical impossibility without the secret.",
                "Rate limiting is a related defense, but it does not authenticate. A patient attacker can avoid rate limits and still forge any payload they like. Authentication is what HMAC provides; rate limiting is a separate layer.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "Why is the dedup set scoped to a time window, not kept forever?",
            [
                "Because the set would grow without bound. Pairing it with a tight replay window means the Service only has to remember events from the last few minutes.",
                "Because old events become invalid and the dedup logic stops working.",
                "Because the processor stops sending old events to your Service.",
            ],
            [
                "Right. The window bounds the memory cost. A production-grade processor sends a timestamp on every webhook, and the Service refuses any webhook whose timestamp is outside the window (say, more than 5 minutes off the Service's clock). That window also bounds how long the dedup set must keep each event_id. After the window, events drop out of the set safely because the timestamp check would reject them anyway.",
                "Old events do not 'become invalid' on their own. The Service makes them invalid by enforcing the timestamp window. Without the enforcement, an old event_id would still match in the dedup set if it stuck around.",
                "Processors typically do not stop retrying webhooks — they retry until acknowledged. Your Service has to handle bounded retries gracefully (return 2xx within a window to stop retries; outside the window, the duplicate gets caught by the dedup set instead).",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "Which building blocks does the production webhook receiver naturally use?",
            [
                "Service for the endpoint, Key-Value Store for the dedup set (with TTL = the replay window), and a clock from the Time entity for the timestamp check.",
                "Just a Service. Webhooks are simple HTTP endpoints.",
                "Vector Database, because the dedup set is a similarity search.",
            ],
            [
                "Exactly. The Service handles the inbound HTTP. The Key-Value Store with TTL is the natural home for the dedup set (event_id → timestamp seen). The Time entity is the source of truth for 'now' against which the X-Processor-Timestamp is compared. This is a small composition, but it is the canonical secure-webhook shape.",
                "A bare Service does not protect against forgeries or replays. The dedup state lives somewhere. The right somewhere is a Key-Value Store, scoped to the replay window. Without it, every webhook is unprotected.",
                "Vector Database is for semantic similarity. The webhook dedup is exact match on event_id. Wrong tool. Key-Value Store with TTL is the right primitive.",
            ],
            correct_index=0,
        )

    # =======================================================================
    # Summary
    # =======================================================================

    def show_summary(self):
        self.print_header("LAB COMPLETE — SUMMARY")
        total = sum(self.experiment_times.values()) if self.experiment_times else 0.0
        for label, secs in self.experiment_times.items():
            print(f"   {label}: {secs:.2f}s")
        print(f"   total runtime: {total:.2f}s")

        print()
        print(f"   Reflection questions answered: {self.total_questions}")
        print(f"   Correct on first guess:        {self.correct_answers}")
        if self.total_questions:
            pct = (self.correct_answers / self.total_questions) * 100
            print(f"   First-guess accuracy:          {pct:.0f}%")

        self.print_info("""
What you should carry forward:

• The Queue is the seam that moves slow External Service calls off the
  user's request path. Sync designs make the user wait. Async designs
  make the Worker wait instead.

• Idempotency keys are the deduplication handle that lets a retry be
  safe. The key represents the intent, not the attempt. Same intent,
  same key, on every retry.

• A timeout is not a "did not happen" signal. The External Service may
  have done the work and the response was lost. Idempotency keys let
  the retry confirm what already happened.

• Webhooks are inbound calls from outside your trust boundary. Verify
  the HMAC signature, enforce a replay window with the Time entity,
  and dedup by event_id in a Key-Value Store. Three checks. Three
  attacks defeated.

• 'Two checks, three checks' is the senior shape. Junior engineers do
  one. Seniors stack the defenses so a single failed check does not
  ship a bug.

In every Course IV case study from here on, Service plus External
Service is where the platform meets the world. Now you have felt the
patterns that keep that boundary correct.
""")
        print(f"\n🏆 Lab 2 complete, {self.student_name}. Onward.\n")

    # =======================================================================
    # Orchestration
    # =======================================================================

    def run_full(self):
        self.run_welcome()
        self.experiment_1_sync_vs_queue()
        self.experiment_2_idempotency_on_timeout()
        self.experiment_3_webhook_signature_and_replay()
        self.show_summary()

    def run_one(self, experiment_num: int):
        mapping = {
            1: self.experiment_1_sync_vs_queue,
            2: self.experiment_2_idempotency_on_timeout,
            3: self.experiment_3_webhook_signature_and_replay,
        }
        fn = mapping.get(experiment_num)
        if fn is None:
            print(f"Unknown experiment: {experiment_num}. Choose 1-3.")
            return
        print(f"\n  Running Experiment {experiment_num} directly...\n")
        fn()

    def run_non_interactive(self):
        self.instant_print = True

        def _auto_enter(prompt=""):
            return ""

        def _auto_yes(question):
            return True

        def _auto_mc(question, choices, responses, correct_index=0):
            self.total_questions += 1
            self.correct_answers += 1
            return choices[correct_index]

        self.wait_for_enter = _auto_enter
        self.ask_yes_no = _auto_yes
        self.ask_multiple_choice = _auto_mc

        self.student_name = "Tester"
        self.print_info("Running in non-interactive mode (--no-interactive).")
        self.experiment_1_sync_vs_queue()
        self.experiment_2_idempotency_on_timeout()
        self.experiment_3_webhook_signature_and_replay()
        self.show_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Course 4 Lab 2: Service + External Service Discovery"
    )
    parser.add_argument("experiment", nargs="?", type=int,
                        help="Optional experiment number (1-3) to run directly")
    parser.add_argument("--instant", action="store_true",
                        help="Disable typewriter effect (faster output)")
    parser.add_argument("--skip-typewriter", action="store_true",
                        help="Alias for --instant: disable typewriter effect")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Run all experiments without prompts (for CI)")
    args = parser.parse_args()

    lab = LabExperience()
    if args.instant or args.skip_typewriter:
        lab.instant_print = True

    if args.no_interactive:
        lab.run_non_interactive()
    elif args.experiment is None:
        lab.run_full()
    else:
        lab.run_one(args.experiment)


if __name__ == "__main__":
    main()
