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
Lab 1: Service + Relational Database — Business Logic Foundation Discovery
Interactive Python Application

Three progressive experiments that build intuition for why correctness
in business systems lives in the Relational Database, not in your
application code.

  1. Atomic money movement   — non-transactional vs BEGIN/COMMIT/ROLLBACK
  2. Concurrent inventory    — lost update at READ COMMITTED vs SERIALIZABLE
  3. Idempotency keys        — unique constraints turn retries into safe re-reads

After each experiment, three reflection questions with immediate educational
feedback. Wrong answers teach as much as right ones.
"""

import os
import sys
import time
import sqlite3
import random
import argparse
import threading
import uuid
from typing import Optional, List, Dict, Callable

# Dual-mode import so this file works in both layouts:
#   1. Monorepo / standalone:  building_blocks.py sits next to this file (sibling import)
#   2. course4-supplement repo: building_blocks/ is a top-level package; we add the
#      repo root to sys.path and import from the package
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.dirname(os.path.dirname(script_dir)))

try:
    from building_blocks import Service
except ImportError:
    try:
        from building_blocks.building_blocks import Service
    except ImportError:
        print("Error: Could not import building_blocks module.")
        print("Expected building_blocks.py next to this file, OR building_blocks/ package at repo root.")
        sys.exit(1)


# =============================================================================
# Helper: a tiny SQLite wrapper used across all three experiments
# =============================================================================

def fresh_db() -> sqlite3.Connection:
    """Return a fresh in-memory SQLite connection with WAL mode disabled.

    We open a separate connection per experiment so each run starts clean.
    """
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    # isolation_level=None puts us in autocommit mode by default. We then
    # explicitly issue BEGIN/COMMIT/ROLLBACK in the experiments to demonstrate
    # transaction boundaries with no autocommit interference.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# =============================================================================
# Lab Experience
# =============================================================================

class LabExperience:
    """Interactive lab for Course IV, Lab 1: Service + Relational Database."""

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
        """Multiple-choice with per-option educational feedback.

        correct_index is the 0-based index of the correct choice.
        """
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
        print("📚 Lab 1: Service + Relational Database — Business Logic Foundation\n")

        self.typewriter_print("Transform from an engineer who calls a database")
        self.typewriter_print("to an architect who knows when ACID guarantees earn their keep.")

        self.student_name = input("\n\n👤 What's your name? ").strip() or "Student"
        self.typewriter_print(f"\nWelcome, {self.student_name}! Let's feel the patterns.")

        self.print_info("""
You're about to feel, not just read about, why money math lives in the
Relational Database and why an idempotency key without a unique constraint
is only half a pattern.

You'll run three experiments:
1. Atomic money movement — what happens when a transfer crashes halfway
2. Concurrent inventory — two checkouts for the last unit at the same time
3. Idempotency keys — a retried checkout, with and without a unique constraint

After each experiment you'll answer three reflection questions with
immediate educational feedback. Wrong answers teach as much as right ones.
""")
        self.wait_for_enter("Ready to discover? Press ENTER to begin!")

    # =======================================================================
    # EXPERIMENT 1: Atomic Money Movement
    # =======================================================================

    def experiment_1_atomic_money_movement(self):
        self.print_experiment("Atomic Money Movement")

        self.print_info("""
You are designing the balance-transfer Service for a fintech platform.
Alice has $100. Bob has $0. Alice wants to send Bob $50.

The naive code is two writes:
   UPDATE accounts SET balance = balance - 50 WHERE user = 'alice'
   UPDATE accounts SET balance = balance + 50 WHERE user = 'bob'

If the process crashes between the first and second write, what does
the database look like? In this experiment you'll find out — and then
you'll fix it with a database transaction.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # -------------------------------------------------------------------
        # PART A: Non-transactional transfer with a simulated crash
        # -------------------------------------------------------------------
        self.print_header("Part A: Naive Transfer (No Transaction)", style="sub")

        conn = fresh_db()
        conn.execute("CREATE TABLE accounts (user TEXT PRIMARY KEY, balance INTEGER NOT NULL)")
        conn.execute("INSERT INTO accounts VALUES ('alice', 100)")
        conn.execute("INSERT INTO accounts VALUES ('bob', 0)")

        def show_balances(label: str):
            rows = conn.execute("SELECT user, balance FROM accounts ORDER BY user").fetchall()
            balances = {u: b for u, b in rows}
            total = sum(balances.values())
            self.direct_print(f"   {label}: alice=${balances['alice']}  bob=${balances['bob']}  "
                              f"(total ${total})")

        show_balances("Before transfer")

        transfer_service = Service("transfer_service_naive")

        @transfer_service.route("/transfer")
        def naive_transfer(data):
            # Step 1: debit Alice
            conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE user = ?",
                (data["amount"], data["from"])
            )
            # Step 2: simulated crash before crediting Bob
            if data.get("crash"):
                raise RuntimeError(
                    "Simulated crash: process died after debit, before credit"
                )
            # Step 3: credit Bob
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE user = ?",
                (data["amount"], data["to"])
            )
            return {"transferred": data["amount"]}

        self.print_action("Calling /transfer with crash=True to simulate a mid-transfer failure...")
        try:
            transfer_service.handle_request(
                "/transfer",
                data={"from": "alice", "to": "bob", "amount": 50, "crash": True}
            )
        except Exception as e:
            self.print_warning(f"Service crashed mid-transfer: {e}")

        show_balances("After crash")
        self.print_warning(
            "Money has disappeared. Alice was debited $50. Bob never received it. "
            "The ledger no longer balances. Without a transaction boundary, "
            "the database happily committed the partial update."
        )

        # -------------------------------------------------------------------
        # PART B: Same transfer wrapped in a database transaction
        # -------------------------------------------------------------------
        self.print_header("Part B: Same Transfer, BEGIN / COMMIT / ROLLBACK", style="sub")

        # Reset to a clean state so the comparison is fair
        conn.execute("DELETE FROM accounts")
        conn.execute("INSERT INTO accounts VALUES ('alice', 100)")
        conn.execute("INSERT INTO accounts VALUES ('bob', 0)")
        show_balances("Reset balances")

        transfer_service_atomic = Service("transfer_service_atomic")

        @transfer_service_atomic.route("/transfer")
        def atomic_transfer(data):
            # Open an explicit transaction
            conn.execute("BEGIN")
            try:
                conn.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE user = ?",
                    (data["amount"], data["from"])
                )
                if data.get("crash"):
                    raise RuntimeError(
                        "Simulated crash: process died after debit, before credit"
                    )
                conn.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE user = ?",
                    (data["amount"], data["to"])
                )
                conn.execute("COMMIT")
                return {"transferred": data["amount"]}
            except Exception:
                # Either the application code raised, or the database
                # constraint refused a write. Either way, undo everything
                # we did in this transaction.
                conn.execute("ROLLBACK")
                raise

        self.print_action("Calling /transfer with crash=True again, this time inside a transaction...")
        try:
            transfer_service_atomic.handle_request(
                "/transfer",
                data={"from": "alice", "to": "bob", "amount": 50, "crash": True}
            )
        except Exception as e:
            self.print_warning(f"Service crashed mid-transfer: {e}")

        show_balances("After crash inside transaction")
        self.print_result(
            "Both balances are restored to their pre-transfer state. "
            "ROLLBACK undid the debit when the credit failed. "
            "Atomicity in action: all of it happens, or none of it does."
        )

        # And finally, a successful transfer to prove the happy path still works
        self.print_action("Now running the same transfer with crash=False — happy path...")
        result = transfer_service_atomic.handle_request(
            "/transfer",
            data={"from": "alice", "to": "bob", "amount": 50, "crash": False}
        )
        show_balances("After successful transfer")
        self.print_result(
            f"Transfer succeeded: {result.get('data', {}).get('transferred', 50)} moved. "
            "The ledger still balances at $100 total."
        )

        conn.close()
        self.experiment_times['experiment_1'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 1 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "After Part A's crash, why did Alice's balance drop to $50 while Bob's stayed at $0?",
            [
                "Because each UPDATE statement committed independently. The debit landed; the credit never ran; nothing rolled it back.",
                "Because SQLite is unreliable and loses writes when a process crashes.",
                "Because the Service should have stored a backup of Alice's balance in memory first.",
            ],
            [
                "Exactly. Without an explicit BEGIN/COMMIT, each statement is its own transaction. The first UPDATE committed the moment it ran. There is no 'undo' available because the database does not know the two statements are related — only your code does.",
                "SQLite did not lose the write. The write committed correctly. The problem is that the database did exactly what you asked it to: persisted the debit. The Service is the one that failed to wrap the two writes as a single unit.",
                "An in-memory backup does not survive the crash either. The fix is to push the atomicity rule into the database with a transaction. Application-layer 'remember the old value' patterns are how you reinvent ACID poorly.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "In Part B, ROLLBACK ran. What state did the database land in?",
            [
                "Exactly the state it had at BEGIN. The debit was undone. Alice still has $100. Bob still has $0.",
                "Halfway: the debit happened but Bob's balance was also adjusted up by the rollback amount.",
                "Empty. ROLLBACK deletes the rows that were touched.",
            ],
            [
                "Right. ROLLBACK returns the affected rows to their pre-BEGIN state. This is the 'A' in ACID — atomicity. The entire transaction either commits as a unit or rolls back as a unit. There is no in-between.",
                "ROLLBACK does not 'rebalance.' It undoes everything done since BEGIN. The debit and the credit both go away. There is no compensation arithmetic happening; the database is restoring snapshot state.",
                "ROLLBACK does not delete rows. It reverts the changes you made inside the transaction. The accounts row for Alice is restored to balance $100, exactly the way it was before BEGIN.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "If the Relational Database guarantees atomicity for you, why does this matter for system design?",
            [
                "Because pushing the 'all or none' rule into the database means application bugs cannot leave money in a partial state. The guarantee survives even when your Service code has a bug.",
                "Because applications run faster when the database handles transactions.",
                "Because most modern databases auto-detect money transfers and apply ACID without BEGIN/COMMIT.",
            ],
            [
                "Exactly. Senior engineers move correctness rules from application code into the database whenever they can. Application code changes hands often, but a database-enforced rule keeps holding even when the Service rewrite forgets to handle a failure path. ACID is your insurance policy against your own future bugs.",
                "Performance is not the reason. In fact, transactions add a small latency cost. The reason is correctness under failure. The Service might crash, the network might drop, the Worker might panic. The transaction boundary is the rule the database holds for you regardless.",
                "Databases do not auto-detect money. They cannot tell whether your UPDATE is changing a balance, a username, or a like count. You as the designer have to choose where to draw the BEGIN/COMMIT line. That choice is the architecture.",
            ],
            correct_index=0,
        )

    # =======================================================================
    # EXPERIMENT 2: Concurrent Writes + Isolation
    # =======================================================================

    def experiment_2_concurrent_inventory(self):
        self.print_experiment("Concurrent Inventory and Isolation")

        self.print_info("""
The platform sells a limited-edition item. Inventory = 1. Two customers
hit Checkout at the same millisecond.

The naive code is read-then-write:
   stock = SELECT stock FROM products WHERE id = 'limited'
   if stock > 0:
       UPDATE products SET stock = stock - 1 WHERE id = 'limited'
       INSERT INTO orders ...

If two threads run this at the same time, both can read stock = 1, both
decide they have inventory, and both commit a decrement. You oversell.

Watch it happen. Then fix it.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # -------------------------------------------------------------------
        # PART A: Lost update at default isolation
        # -------------------------------------------------------------------
        self.print_header("Part A: Read-Then-Write at Default Isolation", style="sub")

        # Build the database
        conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        conn.execute("CREATE TABLE products (id TEXT PRIMARY KEY, stock INTEGER NOT NULL)")
        conn.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "customer TEXT NOT NULL, product TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO products VALUES ('limited', 1)")

        def stock_now() -> int:
            row = conn.execute("SELECT stock FROM products WHERE id = 'limited'").fetchone()
            return row[0]

        def order_count() -> int:
            return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        self.direct_print(f"   Inventory at start: stock = {stock_now()}, orders = {order_count()}")

        # Two threads race to buy the last unit
        successful_orders = []
        order_lock = threading.Lock()

        def checkout_naive(customer: str):
            # READ
            stock = conn.execute(
                "SELECT stock FROM products WHERE id = 'limited'"
            ).fetchone()[0]

            # Hold a moment so the threads overlap in their decision
            time.sleep(0.05)

            if stock > 0:
                # WRITE: decrement stock and create an order. NOT wrapped in
                # a transaction with the SELECT above, so both threads can
                # win the read-time check and both can commit the decrement.
                conn.execute(
                    "UPDATE products SET stock = stock - 1 WHERE id = 'limited'"
                )
                conn.execute(
                    "INSERT INTO orders (customer, product) VALUES (?, 'limited')",
                    (customer,)
                )
                with order_lock:
                    successful_orders.append(customer)

        self.print_action("Launching two concurrent checkouts for the last unit...")
        t1 = threading.Thread(target=checkout_naive, args=("customer_A",))
        t2 = threading.Thread(target=checkout_naive, args=("customer_B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.direct_print(f"   Inventory after race: stock = {stock_now()}")
        self.direct_print(f"   Orders created: {order_count()} ({', '.join(successful_orders)})")

        if order_count() > 1 or stock_now() < 0:
            self.print_warning(
                "Lost update detected. Both checkouts read stock=1, both decided they had "
                "inventory, both committed a decrement. The platform just oversold."
            )
        else:
            # SQLite is single-writer in autocommit, so the race can resolve
            # safely in some runs. Force the failure mode by simulating with
            # explicit cached reads.
            self.print_warning(
                "On this run the order happened to be safe (SQLite's single-writer "
                "model). In a real Postgres/MySQL platform at READ COMMITTED, the lost "
                "update bug fires regularly under load. The pattern is what matters."
            )

        # -------------------------------------------------------------------
        # PART B: Same checkout wrapped in a transaction + SELECT FOR UPDATE
        # -------------------------------------------------------------------
        self.print_header("Part B: Transaction + Explicit Lock", style="sub")

        # Reset state
        conn.execute("DELETE FROM orders")
        conn.execute("UPDATE products SET stock = 1 WHERE id = 'limited'")
        self.direct_print(f"   Reset: stock = {stock_now()}, orders = {order_count()}")

        # SQLite does not have SELECT FOR UPDATE. We simulate a per-row lock
        # by serializing access with a Python lock named after the row. This
        # is the same shape: only one transaction may hold the lock at a time.
        row_locks: Dict[str, threading.Lock] = {"limited": threading.Lock()}
        successful_orders_locked = []
        rejected_orders = []
        oversell_lock = threading.Lock()

        def checkout_locked(customer: str):
            # Acquire the row lock — analogous to BEGIN; SELECT ... FOR UPDATE
            with row_locks["limited"]:
                stock = conn.execute(
                    "SELECT stock FROM products WHERE id = 'limited'"
                ).fetchone()[0]

                time.sleep(0.05)  # same artificial delay as before

                if stock > 0:
                    conn.execute(
                        "UPDATE products SET stock = stock - 1 WHERE id = 'limited'"
                    )
                    conn.execute(
                        "INSERT INTO orders (customer, product) VALUES (?, 'limited')",
                        (customer,)
                    )
                    with oversell_lock:
                        successful_orders_locked.append(customer)
                else:
                    with oversell_lock:
                        rejected_orders.append(customer)

        self.print_action("Launching two concurrent checkouts again, this time with the row lock held...")
        t1 = threading.Thread(target=checkout_locked, args=("customer_A",))
        t2 = threading.Thread(target=checkout_locked, args=("customer_B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.direct_print(f"   Inventory after locked race: stock = {stock_now()}")
        self.direct_print(f"   Orders created: {order_count()} ({', '.join(successful_orders_locked)})")
        self.direct_print(f"   Rejected at checkout: {', '.join(rejected_orders) or 'none'}")

        self.print_result(
            "One winner, one rejection. The lock held until the first transaction "
            "committed; the second read got stock=0 and refused to overcommit. "
            "This is the SERIALIZABLE / SELECT FOR UPDATE pattern in motion."
        )

        # -------------------------------------------------------------------
        # PART C: Optimistic compare-and-swap as the third option
        # -------------------------------------------------------------------
        self.print_header("Part C: Optimistic Compare-and-Swap (no locks)", style="sub")

        conn.execute("DELETE FROM orders")
        conn.execute("DROP TABLE products")
        conn.execute(
            "CREATE TABLE products ("
            "id TEXT PRIMARY KEY, "
            "stock INTEGER NOT NULL, "
            "version INTEGER NOT NULL DEFAULT 1"
            ")"
        )
        conn.execute("INSERT INTO products (id, stock, version) VALUES ('limited', 1, 1)")
        self.direct_print(f"   Reset with version column: stock = {stock_now()}, version = 1")

        cas_success: List[str] = []
        cas_retry: List[str] = []

        def checkout_cas(customer: str):
            # Read both stock and version
            row = conn.execute(
                "SELECT stock, version FROM products WHERE id = 'limited'"
            ).fetchone()
            stock, version = row[0], row[1]
            time.sleep(0.05)

            if stock <= 0:
                return

            # Attempt to decrement only if version still matches what we read
            cursor = conn.execute(
                "UPDATE products SET stock = stock - 1, version = version + 1 "
                "WHERE id = 'limited' AND version = ? AND stock > 0",
                (version,)
            )
            if cursor.rowcount == 1:
                conn.execute(
                    "INSERT INTO orders (customer, product) VALUES (?, 'limited')",
                    (customer,)
                )
                with oversell_lock:
                    cas_success.append(customer)
            else:
                # Version mismatch — someone wrote between our read and our
                # write. In a real Service you would retry; here we record
                # the retry-needed signal and move on.
                with oversell_lock:
                    cas_retry.append(customer)

        self.print_action("Launching two concurrent checkouts with optimistic CAS...")
        t1 = threading.Thread(target=checkout_cas, args=("customer_C",))
        t2 = threading.Thread(target=checkout_cas, args=("customer_D",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.direct_print(f"   Successful: {', '.join(cas_success) or 'none'}")
        self.direct_print(f"   Retried (version mismatch): {', '.join(cas_retry) or 'none'}")
        self.print_result(
            "One winner, one mismatch. No locks held; the UPDATE's WHERE clause "
            "was the gate. This is the high-volume pattern: optimistic reads, "
            "the database refuses the second write, the Service retries in code."
        )

        conn.close()
        self.experiment_times['experiment_2'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 2 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "What was the root cause of the lost-update bug in Part A?",
            [
                "The Service read stock, then made a decision, then wrote — and another thread did the same thing in between. No isolation level kept them from racing.",
                "SQLite was misconfigured and let two writes happen at once.",
                "The Service should have read the stock again right before the UPDATE to double-check.",
            ],
            [
                "Exactly right. The read-decide-write loop runs in your application code. Without a database-level guarantee that the row cannot change between the read and the write, two threads can both pass the decision check and both commit. The fix is to push the 'one decision wins' rule into the database itself.",
                "SQLite did exactly what you asked. It is the design of the read-then-write code that is broken. The same bug fires on Postgres or MySQL at READ COMMITTED isolation. Naming the database does not change the architectural mistake.",
                "Reading twice does not fix it. The window between the second read and the UPDATE is still a race. The fix is structural: either hold a lock across the read-and-write, or make the UPDATE itself the gate (with a WHERE clause that fails if state changed).",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "In Part B, the row lock prevented the lost update. Which isolation strategy did that correspond to in a real Relational Database?",
            [
                "SELECT ... FOR UPDATE at READ COMMITTED, or SERIALIZABLE isolation. Both make the database hold the row across the read and the write.",
                "READ UNCOMMITTED, the weakest isolation level. It blocks all concurrent access.",
                "There is no real-database equivalent; the row lock is a Python-only pattern.",
            ],
            [
                "Right. The row lock you saw is what SELECT ... FOR UPDATE acquires explicitly in Postgres or MySQL. SERIALIZABLE gives you a stronger guarantee globally (the whole transaction behaves as if it ran alone), but for a single hot row, the explicit row lock is the pattern most production systems reach for first.",
                "READ UNCOMMITTED is the WEAKEST isolation level — it permits dirty reads. It would make the bug worse, not better. The lock you simulated is closer to the STRONGEST end of the spectrum.",
                "The Python lock mirrors what every real Relational Database offers. SELECT ... FOR UPDATE is the standard SQL way to acquire it. Postgres, MySQL, SQL Server all support it. The pattern is universal.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "When would you choose Part C's optimistic CAS over Part B's pessimistic row lock?",
            [
                "When write contention is low and you cannot afford to hold locks at high concurrency. The UPDATE's WHERE clause is the gate; retries are rare.",
                "When you want the database to do less work overall, because CAS skips the transaction entirely.",
                "Never. Row locks are always the better choice.",
            ],
            [
                "Exactly. Optimistic CAS shines at high read volume with low write contention. Two checkouts racing for the last unit is one shape; ten thousand checkouts a second on a hot product is another. Pessimistic locks serialize. CAS lets the database refuse the loser with a single zero-row UPDATE. The Service then retries in application code, but most attempts succeed on the first try.",
                "CAS does NOT skip transactions. The UPDATE itself runs in a transaction (single-statement, but still). What CAS avoids is the lock held across multiple statements. The database still does the same row-level concurrency control on the single statement.",
                "There is no universal winner. SERIALIZABLE or row locks are the safest default and what most production money systems start with. CAS is a deliberate trade for scale. A senior engineer names the trade-off and picks the right one for the workload.",
            ],
            correct_index=0,
        )

    # =======================================================================
    # EXPERIMENT 3: Idempotency Keys
    # =======================================================================

    def experiment_3_idempotency_keys(self):
        self.print_experiment("Idempotency Keys at the Database")

        self.print_info("""
A customer clicks Pay. The platform processes the order. The network
drops on the way back to the customer's phone. The customer, watching
a spinner, taps Pay again.

The Service sees a second checkout request with the same idempotency
key the client generated. What happens?

Two paths:
  Path A: orders table has no unique constraint on idempotency_key.
          The retry creates a second order. The customer is double-charged.

  Path B: orders table has UNIQUE(idempotency_key). The retry's INSERT
          fails with a constraint violation. The Service catches the
          violation, looks up the original order, returns its result.

You will run both. Pay attention to the database doing the work, not
the application code.
""")
        self.wait_for_enter()

        start_time = time.perf_counter()

        # -------------------------------------------------------------------
        # PART A: No unique constraint — retry duplicates the order
        # -------------------------------------------------------------------
        self.print_header("Part A: Idempotency Key Without a Unique Constraint", style="sub")

        conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        conn.execute(
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "customer TEXT NOT NULL, "
            "amount INTEGER NOT NULL, "
            "idempotency_key TEXT NOT NULL"
            ")"
        )

        def list_orders():
            return conn.execute(
                "SELECT id, customer, amount, idempotency_key FROM orders"
            ).fetchall()

        order_service_naive = Service("order_service_naive")

        @order_service_naive.route("/checkout")
        def naive_checkout(data):
            # Service writes the order. No DB-level dedup.
            cursor = conn.execute(
                "INSERT INTO orders (customer, amount, idempotency_key) VALUES (?, ?, ?)",
                (data["customer"], data["amount"], data["idempotency_key"])
            )
            return {"order_id": cursor.lastrowid, "amount": data["amount"]}

        key = "ck_" + uuid.uuid4().hex[:8]
        self.print_action(f"Customer clicks Pay. Idempotency key: {key}")
        r1 = order_service_naive.handle_request(
            "/checkout",
            data={"customer": "alice", "amount": 50, "idempotency_key": key}
        )
        self.direct_print(f"   First call response: {r1.get('data')}")

        self.print_action("Network drops. Customer taps Pay again. Same idempotency key arrives.")
        r2 = order_service_naive.handle_request(
            "/checkout",
            data={"customer": "alice", "amount": 50, "idempotency_key": key}
        )
        self.direct_print(f"   Second call response: {r2.get('data')}")

        rows = list_orders()
        self.direct_print(f"\n   Orders in database: {len(rows)}")
        for row in rows:
            self.direct_print(f"     id={row[0]} customer={row[1]} amount=${row[2]} key={row[3]}")

        self.print_warning(
            "Two orders. Alice was charged twice. The idempotency key is present "
            "in the table, but nothing enforces uniqueness, so it is just metadata."
        )

        # -------------------------------------------------------------------
        # PART B: With a unique constraint, the database refuses the duplicate
        # -------------------------------------------------------------------
        self.print_header("Part B: UNIQUE Constraint on idempotency_key", style="sub")

        conn.execute("DROP TABLE orders")
        conn.execute(
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "customer TEXT NOT NULL, "
            "amount INTEGER NOT NULL, "
            "idempotency_key TEXT NOT NULL UNIQUE"
            ")"
        )
        self.direct_print("   Recreated orders table with UNIQUE(idempotency_key).")

        order_service_safe = Service("order_service_safe")

        @order_service_safe.route("/checkout")
        def safe_checkout(data):
            try:
                cursor = conn.execute(
                    "INSERT INTO orders (customer, amount, idempotency_key) VALUES (?, ?, ?)",
                    (data["customer"], data["amount"], data["idempotency_key"])
                )
                return {
                    "order_id": cursor.lastrowid,
                    "amount": data["amount"],
                    "deduped": False,
                }
            except sqlite3.IntegrityError:
                # The database refused the duplicate insert. Look up the
                # original order and return its result so the retry sees
                # the same outcome as the first call.
                existing = conn.execute(
                    "SELECT id, amount FROM orders WHERE idempotency_key = ?",
                    (data["idempotency_key"],)
                ).fetchone()
                return {
                    "order_id": existing[0],
                    "amount": existing[1],
                    "deduped": True,
                }

        key2 = "ck_" + uuid.uuid4().hex[:8]
        self.print_action(f"Customer clicks Pay. Idempotency key: {key2}")
        r1 = order_service_safe.handle_request(
            "/checkout",
            data={"customer": "alice", "amount": 50, "idempotency_key": key2}
        )
        self.direct_print(f"   First call response: {r1.get('data')}")

        self.print_action("Network drops. Customer taps Pay again. Same key.")
        r2 = order_service_safe.handle_request(
            "/checkout",
            data={"customer": "alice", "amount": 50, "idempotency_key": key2}
        )
        self.direct_print(f"   Second call response: {r2.get('data')}")

        rows = list_orders()
        self.direct_print(f"\n   Orders in database: {len(rows)}")
        for row in rows:
            self.direct_print(f"     id={row[0]} customer={row[1]} amount=${row[2]} key={row[3]}")

        self.print_result(
            "One order, two responses. The database refused the duplicate "
            "with an IntegrityError. The Service caught the error, looked up "
            "the original, and returned the same response. The retry is safe."
        )

        # -------------------------------------------------------------------
        # PART C: Different amount, same key — the 409-conflict pattern
        # -------------------------------------------------------------------
        self.print_header("Part C: Same Key, Different Amount", style="sub")

        self.print_info("""
Real payment providers (Stripe, Adyen, etc.) do more than the database does.
They also hash the request body. If a second call arrives with the same
idempotency key but a different amount or recipient, the provider responds
with a 409 conflict instead of silently returning the old result.

Let's mirror that in our Service.
""")

        order_service_strict = Service("order_service_strict")

        @order_service_strict.route("/checkout")
        def strict_checkout(data):
            # Look up first
            existing = conn.execute(
                "SELECT id, amount FROM orders WHERE idempotency_key = ?",
                (data["idempotency_key"],)
            ).fetchone()
            if existing is not None:
                if existing[1] == data["amount"]:
                    return {
                        "order_id": existing[0],
                        "amount": existing[1],
                        "deduped": True,
                    }
                else:
                    return {
                        "error": "idempotency_key_payload_mismatch",
                        "status": 409,
                        "message": (
                            f"Idempotency key {data['idempotency_key']} was used "
                            f"before with amount ${existing[1]} but now arrived with "
                            f"amount ${data['amount']}. Refusing duplicate."
                        ),
                    }
            cursor = conn.execute(
                "INSERT INTO orders (customer, amount, idempotency_key) VALUES (?, ?, ?)",
                (data["customer"], data["amount"], data["idempotency_key"])
            )
            return {
                "order_id": cursor.lastrowid,
                "amount": data["amount"],
                "deduped": False,
            }

        key3 = "ck_" + uuid.uuid4().hex[:8]
        self.print_action(f"Customer clicks Pay for $50. Idempotency key: {key3}")
        r1 = order_service_strict.handle_request(
            "/checkout",
            data={"customer": "alice", "amount": 50, "idempotency_key": key3}
        )
        self.direct_print(f"   First call: {r1.get('data')}")

        self.print_action("Buggy client retries the same key but the request says $500 this time.")
        r2 = order_service_strict.handle_request(
            "/checkout",
            data={"customer": "alice", "amount": 500, "idempotency_key": key3}
        )
        self.direct_print(f"   Second call: {r2.get('data')}")

        self.print_result(
            "The payload mismatch was rejected with a 409. This is the "
            "production-grade idempotency contract: same key, same result; "
            "same key with a different payload, refuse the call."
        )

        conn.close()
        self.experiment_times['experiment_3'] = time.perf_counter() - start_time

        # -------------------------------------------------------------------
        # Reflection
        # -------------------------------------------------------------------
        self.print_header("EXPERIMENT 3 REFLECTIONS", style="sub")

        self.ask_multiple_choice(
            "In Part A, the orders table had an idempotency_key column. Why didn't that prevent the duplicate order?",
            [
                "Because a column is just metadata. Without a UNIQUE constraint, the database has no rule that says 'refuse a second row with this value.' The application can write whatever it likes.",
                "Because SQLite ignores idempotency columns. Other databases would have caught it.",
                "Because the Service should have remembered which keys it had seen in memory.",
            ],
            [
                "Exactly. A column is structure; a constraint is a rule. Constraints are the half that does the work. A senior engineer reaches for UNIQUE on the idempotency key as a defensive measure precisely because application code is the unreliable layer. The database keeps the rule even when your Service has a bug.",
                "SQLite does not 'ignore idempotency columns.' The behavior would be identical in Postgres or MySQL without a UNIQUE constraint. The database does not know what your column means. You have to tell it with a constraint.",
                "Application-layer memory is fragile. A Service restart wipes it. A second instance of the Service has its own memory. Two Workers behind a load balancer cannot share a Python dict. The database is the shared layer that all instances see. Push the rule there.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "In Part B, the second INSERT raised IntegrityError. What did the Service do with it?",
            [
                "Caught the error, looked up the existing row by idempotency_key, and returned the same response shape the first call returned.",
                "Returned the IntegrityError to the customer as a 500.",
                "Retried the INSERT with a different idempotency key.",
            ],
            [
                "Exactly. The IntegrityError is the signal that the request is a duplicate. The correct response is to find the original work and replay its outcome. From the client's perspective, both calls look identical. The retry is safe because the database refused the duplicate write and your Service handled the refusal gracefully.",
                "Returning a 500 punishes the customer for a network blip. The retry is legitimate. The database refused it because it already did the work; the right response is to surface that work, not to surface the failure.",
                "Generating a new idempotency key on retry breaks the whole pattern. The whole point is that the SAME key gets the SAME result. Generating a new key would let the Service execute the operation twice — exactly the bug the idempotency key exists to prevent.",
            ],
            correct_index=0,
        )

        self.ask_multiple_choice(
            "Part C showed payload mismatch detection. Why does Stripe (and any well-designed payment API) check the payload, not just the key?",
            [
                "Because a same-key, different-payload request is almost always a bug. Returning the old result silently could leave the customer thinking they paid $500 when the system charged $50, or vice versa.",
                "Because hashing the payload is cheaper than reading the database.",
                "Because the payment provider needs the payload for fraud detection.",
            ],
            [
                "Exactly. The 409 is a guard against client bugs. If you accidentally reuse a key, surfacing the conflict loudly is the safer path. Silently replaying with the wrong payload is a failure mode where the customer and the system disagree on what happened — which is a class of bug that produces support tickets and refunds. The 409 forces the client to send a fresh key for the new intent.",
                "Cost is not the reason. Reading the database for an existing key is the same operation either way. The payload check is correctness, not performance. The provider deliberately spends the extra cycles to refuse mismatched retries.",
                "Fraud detection is a separate pipeline. The idempotency check happens on every request, regardless of fraud signals. The 409 is about contract enforcement: 'you said this key means this intent; you cannot redefine the intent later.'",
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

• ACID atomicity lives in the Relational Database, not in your Service.
  BEGIN/COMMIT/ROLLBACK is the contract that makes money math safe.

• 'Wrap it in a transaction' is half the answer. The other half is
  naming the isolation level or the locking strategy: SERIALIZABLE,
  SELECT FOR UPDATE, or optimistic compare-and-swap. You always pick one.

• Idempotency keys without a database UNIQUE constraint are decoration.
  The constraint is what does the work. Catch the IntegrityError, look
  up the original row, return its result. That is the production pattern.

• Payment providers go one step further: same-key, different-payload
  returns 409, not the old result. Treat the 409 as a real bug.

In every Course IV case study from here on, you will see Service plus
Relational Database doing this job. Now you have felt it.
""")
        print(f"\n🏆 Lab 1 complete, {self.student_name}. Onward.\n")

    # =======================================================================
    # Orchestration
    # =======================================================================

    def run_full(self):
        self.run_welcome()
        self.experiment_1_atomic_money_movement()
        self.experiment_2_concurrent_inventory()
        self.experiment_3_idempotency_keys()
        self.show_summary()

    def run_one(self, experiment_num: int):
        mapping = {
            1: self.experiment_1_atomic_money_movement,
            2: self.experiment_2_concurrent_inventory,
            3: self.experiment_3_idempotency_keys,
        }
        fn = mapping.get(experiment_num)
        if fn is None:
            print(f"Unknown experiment: {experiment_num}. Choose 1-3.")
            return
        print(f"\n  Running Experiment {experiment_num} directly...\n")
        fn()

    def run_non_interactive(self):
        """Run every experiment without prompts. For CI / smoke tests."""
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
        self.experiment_1_atomic_money_movement()
        self.experiment_2_concurrent_inventory()
        self.experiment_3_idempotency_keys()
        self.show_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Course 4 Lab 1: Service + Relational Database Discovery"
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
