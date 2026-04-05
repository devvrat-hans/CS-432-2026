import copy
import json
import os
import threading
from datetime import datetime, timezone

from database.table import Table
from database.transaction import TransactionContext


class DBManager:
    def __init__(self):
        self.tables = {}
        self.transaction_history = []
        self.trace_logs = []
        self.max_trace_entries = 5000
        self.lock = threading.Lock()
        self.failure_injection = {
            "enabled": False,
            "checkpoint": None,
            "remaining_hits": 0,
        }

        wal_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        self.wal_path = os.path.abspath(os.path.join(wal_dir, "transaction_wal.jsonl"))
        os.makedirs(os.path.dirname(self.wal_path), exist_ok=True)

        self.recovery_report = self.recover_from_wal()
        self.recovery_summary = self._summarize_recovery_report(self.recovery_report)
        self._trace_event(
            transaction_id="system",
            phase="recovery_complete",
            details=self.recovery_summary,
        )

    # ---------------- TRANSACTIONS ----------------

    def _begin_transaction(self, operation, table_name=None):
        tx = TransactionContext(operation=operation, table_name=table_name)
        tx.activate()
        
        self._append_wal_events([{
        "transaction_id": tx.transaction_id,
        "timestamp": self._now_iso(),
        "type": "BEGIN"
    }])
        self._trace_event(
            transaction_id=tx.transaction_id,
            phase="transaction_begin",
            details={"operation": operation, "table_name": table_name},
        )
        return tx

    def _commit_transaction(self, tx):
        if not tx.is_active():
        # Already committed → ignore (idempotent)
            return

        tx.commit()
        self.transaction_history.append(tx)

        self._append_wal_events([{
            "transaction_id": tx.transaction_id,
            "timestamp": self._now_iso(),
            "type": "COMMIT"
        }])

        self._trace_event(
            transaction_id=tx.transaction_id,
            phase="transaction_commit",
            details={"operation": tx.operation, "table_name": tx.table_name},
        )

    def _fail_transaction(self, tx, error):
        tx.mark_failed(str(error))
        self.transaction_history.append(tx)
        self._trace_event(
            transaction_id=tx.transaction_id,
            phase="transaction_failed",
            details={
                "operation": tx.operation,
                "table_name": tx.table_name,
                "error": str(error),
            },
        )

    def _rollback_transaction(self, tx):
        tx.rollback()
        self.transaction_history.append(tx)
        self._trace_event(
            transaction_id=tx.transaction_id,
            phase="transaction_rolled_back",
            details={"operation": tx.operation, "table_name": tx.table_name},
        )

    def get_transaction_history(self):
        return list(self.transaction_history)

    def get_last_transaction(self):
        return self.transaction_history[-1] if self.transaction_history else None

    def _trace_event(self, transaction_id, phase, details=None):
        entry = {
            "timestamp": self._now_iso(),
            "transaction_id": transaction_id,
            "phase": phase,
            "details": details or {},
        }

        self.trace_logs.append(entry)
        if len(self.trace_logs) > self.max_trace_entries:
            self.trace_logs = self.trace_logs[-self.max_trace_entries:]

    def get_trace_logs(self, transaction_id=None, limit=None):
        logs = self.trace_logs
        if transaction_id is not None:
            logs = [entry for entry in logs if entry["transaction_id"] == transaction_id]

        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be >= 1")
            logs = logs[-limit:]

        return list(logs)
    
    # ---------------- PUBLIC TRANSACTION API ----------------

    def begin(self):
        return self._begin_transaction("manual")

    def commit(self, tx):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")

    def rollback(self, tx):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")
        return self._rollback_transaction(tx)

    def get_all_tables(self):
        return list(self.tables.keys())

    def _summarize_recovery_report(self, report):
        summary_text = (
            f"Recovery: committed={report['applied_committed_transactions']}, "
            f"incomplete={report['handled_incomplete_transactions']}, "
            f"malformed={report['malformed_entries']}, "
            f"total_entries={report['total_entries']}"
        )
        return {
            "summary": summary_text,
            "applied_committed_transactions": report["applied_committed_transactions"],
            "handled_incomplete_transactions": report["handled_incomplete_transactions"],
            "malformed_entries": report["malformed_entries"],
            "total_entries": report["total_entries"],
            "committed_tx_ids": list(report.get("committed_tx_ids", [])),
            "incomplete_tx_ids": list(report.get("incomplete_tx_ids", [])),
        }

    def get_recovery_summary(self):
        return dict(self.recovery_summary)

    # ---------------- STAGED MUTATION ENGINE ----------------

    def _clone_tables_state(self):
        return copy.deepcopy(self.tables)

    def _run_staged_mutation(self, tx, mutation_fn):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")

        with self.lock:   #  WHOLE FUNCTION INSIDE

            baseline_tables = self._clone_tables_state()
            staged_tables = self._clone_tables_state()

            self._trace_event(
                transaction_id=tx.transaction_id,
                phase="staged_mutation_start",
                details={"operation": tx.operation, "table_name": tx.table_name},
            )

            try:
                result = mutation_fn(staged_tables)

                self._check_failure_checkpoint("after_index_write")

                self._trace_event(
                    transaction_id=tx.transaction_id,
                    phase="index_write_complete",
                    details={"operation": tx.operation, "table_name": tx.table_name},
                )

                staged_events = self._build_wal_events(tx, staged_tables, status="staged")
                self._append_wal_events(staged_events)

                self._check_failure_checkpoint("after_log_write")

                self._trace_event(
                    transaction_id=tx.transaction_id,
                    phase="wal_staged_written",
                    details={"event_count": len(staged_events)},
                )

                
                self._validate_constraints(staged_tables)
                self._check_failure_checkpoint("after_data_write")
                self.tables = staged_tables
                self._assert_database_consistency(
                    context=f"post-commit:{tx.operation}"
                )

                self._trace_event(
                    transaction_id=tx.transaction_id,
                    phase="data_write_complete",
                    details={"operation": tx.operation, "table_name": tx.table_name},
                )

                self._check_failure_checkpoint("before_commit_marker")

                committed_events = self._build_wal_events(
                    tx, self.tables, status="committed"
                )
                self._append_wal_events(committed_events)
                self._commit_transaction(tx)

                self._trace_event(
                    transaction_id=tx.transaction_id,
                    phase="wal_committed_written",
                    details={"event_count": len(committed_events)},
                )

                return result

            except Exception as error:
                rollback_validation_error = None

                self.tables = baseline_tables

                try:
                    self._assert_database_consistency(
                        context=f"post-rollback:{tx.operation}"
                    )
                except Exception as consistency_error:
                    rollback_validation_error = consistency_error

                    self._trace_event(
                        transaction_id=tx.transaction_id,
                        phase="rollback_consistency_validation_failed",
                        details={"error": str(consistency_error)},
                    )

                tx.mark_failed(str(error))
                self._rollback_transaction(tx)

                rollback_events = self._build_rollback_wal_events(tx)
                self._append_wal_events(rollback_events)

                self._trace_event(
                    transaction_id=tx.transaction_id,
                    phase="rollback_complete",
                    details={"error": str(error), "event_count": len(rollback_events)},
                )

                if rollback_validation_error is not None:
                    raise RuntimeError(
                        f"Mutation failed: {error}; rollback validation failed: {rollback_validation_error}"
                    ) from error

                raise

    def configure_failure_injection(self, checkpoint, trigger_after_hits=1):
        valid = {
            "after_index_write",
            "after_log_write",
            "after_data_write",
            "before_commit_marker",
        }

        if checkpoint not in valid:
            raise ValueError(f"Unsupported failure checkpoint: {checkpoint}")

        if trigger_after_hits < 1:
            raise ValueError("trigger_after_hits must be >= 1")

        self.failure_injection = {
            "enabled": True,
            "checkpoint": checkpoint,
            "remaining_hits": trigger_after_hits,
        }

    def clear_failure_injection(self):
        self.failure_injection = {
            "enabled": False,
            "checkpoint": None,
            "remaining_hits": 0,
        }

    def _check_failure_checkpoint(self, checkpoint):
        config = self.failure_injection

        if not config.get("enabled"):
            return

        if config.get("checkpoint") != checkpoint:
            return

        config["remaining_hits"] -= 1
        if config["remaining_hits"] <= 0:
            self.clear_failure_injection()
            raise RuntimeError(f"Injected failure at checkpoint '{checkpoint}'")

    def _collect_consistency_report(self):
        reports = []
        for table_name in sorted(self.tables.keys()):
            table = self.tables[table_name]
            reports.append(table.consistency_report())
        return reports

    def _assert_database_consistency(self, context="runtime"):
        reports = self._collect_consistency_report()
        failed = [report for report in reports if not report.get("ok")]

        if failed:
            diagnostics = "; ".join(
                f"{item['table']}=>{','.join(item['issues'])}"
                for item in failed
            )
            raise RuntimeError(f"Database consistency violation ({context}): {diagnostics}")

        return reports

    def get_consistency_report(self):
        return self._collect_consistency_report()

    # ---------------- ROLLBACK ENGINE ----------------

    def _rollback_record_snapshot(self, table_name, key, before_value):
        table = self.tables.get(table_name)
        if table is None:
            return

        current_value = table.search(key)

        # Idempotent restoration:
        # - record absent before -> ensure absent
        # - record present before -> ensure value restored
        if before_value is None:
            if current_value is not None:
                table.delete(key)
            return

        if current_value is None:
            table.insert(key, before_value)
        else:
            table.update(key, before_value)

    def _rollback_table_snapshot(self, table_name, before_value):
        # Idempotent restoration:
        # - table absent before -> ensure absent
        # - table present before -> restore prior table object
        if before_value is None:
            if table_name in self.tables:
                del self.tables[table_name]
            return

        self.tables[table_name] = copy.deepcopy(before_value)

    def rollback_transaction(self, transaction_id):
        tx = None
        for candidate in reversed(self.transaction_history):
            if candidate.transaction_id == transaction_id:
                tx = candidate
                break

        if tx is None:
            raise ValueError(f"Transaction '{transaction_id}' not found.")

        snapshots = list(tx.before_snapshots)
        snapshots.reverse()

        for snapshot in snapshots:
            entity_type = snapshot.get("entity_type")
            entity_name = snapshot.get("entity_name")
            key = snapshot.get("key")
            before_value = snapshot.get("before_value")

            if entity_type == "record":
                self._rollback_record_snapshot(entity_name, key, before_value)
            elif entity_type == "table":
                self._rollback_table_snapshot(entity_name, before_value)

        self._assert_database_consistency(context=f"manual-rollback:{transaction_id}")

        tx.rollback()
        self.transaction_history.append(tx)
        self._append_wal_events(self._build_rollback_wal_events(tx))
        return True

    # ---------------- WAL ----------------

    def _serialize_image(self, value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        if isinstance(value, dict):
            return {k: self._serialize_image(v) for k, v in value.items()}

        if isinstance(value, (list, tuple)):
            return [self._serialize_image(item) for item in value]

        return str(value)

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def _append_wal_events(self, events):
        if not events:
            return

        with open(self.wal_path, "a", encoding="utf-8") as wal_file:
            for event in events:
                wal_file.write(json.dumps(event, ensure_ascii=True) + "\n")

            wal_file.flush()
            os.fsync(wal_file.fileno())

        tx_id = events[0].get("transaction_id") if events else "system"
        status = events[0].get("status") if events else "unknown"
        self._trace_event(
            transaction_id=tx_id,
            phase="wal_flush",
            details={"event_count": len(events), "status": status},
        )

    def _build_wal_events(self, tx, staged_tables, status):
        events = []

        for snapshot in tx.before_snapshots:
            entity_type = snapshot.get("entity_type")
            entity_name = snapshot.get("entity_name")
            key = snapshot.get("key")
            before_image = snapshot.get("before_value")

            if entity_type == "record":
                after_image = None
                staged_table = staged_tables.get(entity_name)
                if staged_table is not None:
                    after_image = staged_table.search(key)
                target_entity = f"{entity_name}:{key}"
            else:
                before_image = {"exists": before_image is not None}
                after_image = {"exists": entity_name in staged_tables}
                target_entity = entity_name

            events.append(
                {
                    "transaction_id": tx.transaction_id,
                    "timestamp": self._now_iso(),
                    "operation_type": tx.operation,
                    "table_name": tx.table_name,
                    "target_entity": target_entity,
                    "entity_type": entity_type,
                    "key": key,
                    "status": status,
                    "before_image": self._serialize_image(before_image),
                    "after_image": self._serialize_image(after_image),
                }
            )

        return events

    def _build_rollback_wal_events(self, tx):
        events = []

        for snapshot in tx.before_snapshots:
            entity_type = snapshot.get("entity_type")
            entity_name = snapshot.get("entity_name")
            key = snapshot.get("key")
            before_image = snapshot.get("before_value")

            if entity_type == "record":
                target_entity = f"{entity_name}:{key}"
            else:
                before_image = {"exists": before_image is not None}
                target_entity = entity_name

            events.append(
                {
                    "transaction_id": tx.transaction_id,
                    "timestamp": self._now_iso(),
                    "operation_type": tx.operation,
                    "table_name": tx.table_name,
                    "target_entity": target_entity,
                    "entity_type": entity_type,
                    "key": key,
                    "status": "rolled_back",
                    "before_image": self._serialize_image(before_image),
                    "after_image": self._serialize_image(before_image),
                    "error_message": tx.error_message,
                }
            )

        return events

    # ---------------- CRASH RECOVERY ----------------

    def _ensure_recovery_table(self, table_name):
        if table_name not in self.tables:
            self.tables[table_name] = Table(table_name)
        return self.tables[table_name]

    def _apply_table_image(self, table_name, image):
        exists = bool(image.get("exists")) if isinstance(image, dict) else False
        if exists:
            self._ensure_recovery_table(table_name)
        elif table_name in self.tables:
            del self.tables[table_name]

    def _parse_recovery_key(self, event):
        key = event.get("key")
        if key is not None:
            return key

        target = event.get("target_entity")
        if not isinstance(target, str) or ":" not in target:
            return None

        key_text = target.split(":", 1)[1]
        try:
            return int(key_text)
        except ValueError:
            pass

        return key_text

    def _apply_record_image(self, table_name, key, image):
        if key is None:
            return

        table = self._ensure_recovery_table(table_name)
        current = table.search(key)

        if image is None:
            if current is not None:
                table.delete(key)
            return

        if current is None:
            table.insert(key, image)
        else:
            table.update(key, image)

    def _apply_wal_event_image(self, event, image_type):
        entity_type = event.get("entity_type")
        table_name = event.get("table_name")
        target_entity = event.get("target_entity")
        image = event.get(image_type)

        if entity_type == "table":
            table_target = table_name or str(target_entity)
            self._apply_table_image(table_target, image)
            return

        if entity_type == "record":
            record_table = table_name
            if record_table is None and isinstance(target_entity, str) and ":" in target_entity:
                record_table = target_entity.split(":", 1)[0]

            if record_table is None:
                return

            key = self._parse_recovery_key(event)
            self._apply_record_image(record_table, key, image)

    def recover_from_wal(self):
        report = {
            "applied_committed_transactions": 0,
            "handled_incomplete_transactions": 0,
            "malformed_entries": 0,
            "total_entries": 0,
            "committed_tx_ids": [],
            "incomplete_tx_ids": [],
        }

        if not os.path.exists(self.wal_path):
            return report

        ordered_tx_ids = []
        tx_events = {}

        with open(self.wal_path, "r", encoding="utf-8") as wal_file:
            for line in wal_file:
                raw_line = line.strip()
                if not raw_line:
                    continue

                report["total_entries"] += 1

                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    report["malformed_entries"] += 1
                    continue

                tx_id = event.get("transaction_id")
                status = event.get("status")
                entity_type = event.get("entity_type")
                operation_type = event.get("operation_type")

                if not tx_id or not status or not entity_type or not operation_type:
                    report["malformed_entries"] += 1
                    continue

                if tx_id not in tx_events:
                    tx_events[tx_id] = []
                    ordered_tx_ids.append(tx_id)

                tx_events[tx_id].append(event)

        for tx_id in ordered_tx_ids:
            events = tx_events.get(tx_id, [])
            statuses = {event.get("status") for event in events}

            if "committed" in statuses:
                committed_events = [event for event in events if event.get("status") == "committed"]
                for event in committed_events:
                    self._apply_wal_event_image(event, "after_image")

                report["applied_committed_transactions"] += 1
                report["committed_tx_ids"].append(tx_id)
                continue

            # Incomplete transaction recovery: undo by restoring before images.
            rollback_base = [
                event for event in events if event.get("status") in {"staged", "rolled_back", "failed"}
            ]

            for event in reversed(rollback_base):
                self._apply_wal_event_image(event, "before_image")

            report["handled_incomplete_transactions"] += 1
            report["incomplete_tx_ids"].append(tx_id)

        return report
    def _validate_constraints(self, tables):
        for table_name, table in tables.items():
            for key, value in table.get_all():

                if isinstance(value, dict):

                    #  Balance constraint
                    if "balance" in value and value["balance"] < 0:
                        raise ValueError(
                            f"Negative balance not allowed in table '{table_name}'"
                        )

                    #  Stock constraint
                    if "stock" in value and value["stock"] < 0:
                        raise ValueError(
                            f"Negative stock not allowed in table '{table_name}'"
                        )

    # ---------------- TABLE MANAGEMENT ----------------

    def create_table(self, tx, name, schema=None, order=3, search_key=None):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")
        tx.add_affected_entity("table", name)
        tx.add_before_snapshot("table", name, before_value=self.tables.get(name))

        def mutation(staged_tables):
            if not name:
                raise ValueError("Table name cannot be empty.")

            if name in staged_tables:
                raise ValueError(f"Table '{name}' already exists in database '__default__'")

            table = Table(name)
            staged_tables[name] = table
            return table

        return self._run_staged_mutation(tx, mutation)

    def drop_table(self,tx,  name):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")
        tx.add_affected_entity("table", name)
        tx.add_before_snapshot("table", name, before_value=self.tables.get(name))

        def mutation(staged_tables):
            if name not in staged_tables:
                raise KeyError(f"Table '{name}' does not exist in database '__default__'")

            del staged_tables[name]
            return True

        return self._run_staged_mutation(tx, mutation)

    def list_tables(self):
        return list(self.tables.keys())

    def get_table(self, name):
        if name not in self.tables:
            raise KeyError(f"Table '{name}' does not exist in database '__default__'")
        return self.tables[name]

    def _get_table(self, name):
        return self.get_table(name)

    # ---------------- CRUD ----------------

    def insert(self, tx, table_name, key, value):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")
        tx.add_affected_entity("record", table_name, key=key)

        table = self._get_table(table_name)
        before_value = table.search(key)
        tx.add_before_snapshot("record", table_name, key=key, before_value=before_value)

        def mutation(staged_tables):
            staged_table = staged_tables[table_name]
            staged_table.insert(key, value)
            return True

        return self._run_staged_mutation(tx, mutation)

    def search(self, table_name, key):
        table = self._get_table(table_name)
        return table.search(key)

    def update(self, tx, table_name, key, new_value):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")
        tx.add_affected_entity("record", table_name, key=key)

        table = self._get_table(table_name)
        before_value = table.search(key)
        tx.add_before_snapshot("record", table_name, key=key, before_value=before_value)

        def mutation(staged_tables):
            staged_table = staged_tables[table_name]
            updated = staged_table.update(key, new_value)
            if not updated:
                raise ValueError(f"Key '{key}' not found in table '{table_name}'")
            return True

        return self._run_staged_mutation(tx, mutation)

    def delete(self, tx, table_name, key):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")
        tx.add_affected_entity("record", table_name, key=key)

        table = self._get_table(table_name)
        before_value = table.search(key)
        tx.add_before_snapshot("record", table_name, key=key, before_value=before_value)

        def mutation(staged_tables):
            staged_table = staged_tables[table_name]
            deleted = staged_table.delete(key)
            if not deleted:
                raise ValueError(f"Key '{key}' not found in table '{table_name}'")
            return True

        return self._run_staged_mutation(tx, mutation)

    # ---------------- QUERY ----------------

    def range_query(self, table_name, start_key, end_key):
        if start_key > end_key:
            raise ValueError("start_key cannot be greater than end_key.")

        table = self._get_table(table_name)
        return table.range_query(start_key, end_key)

    def get_all(self, table_name):
        table = self._get_table(table_name)
        return table.get_all()

    # ---------------- BULK ----------------

    def bulk_insert(self,tx, table_name, records):
        if not tx.is_active():
            raise RuntimeError("Transaction is not active")

        tx.add_affected_entity("table", table_name)

        table = self._get_table(table_name)
        keys = [k for k, _ in records]

        for key in keys:
            tx.add_affected_entity("record", table_name, key=key)
            tx.add_before_snapshot("record", table_name, key=key, before_value=table.search(key))

        def mutation(staged_tables):
            staged_table = staged_tables[table_name]

            if len(keys) != len(set(keys)):
                raise ValueError("Duplicate keys found in bulk input.")

            for key in keys:
                if staged_table.search(key) is not None:
                    raise ValueError(f"Key '{key}' already exists in table.")

            for key, value in records:
                staged_table.insert(key, value)

            return True

        return self._run_staged_mutation(tx, mutation)

    # ---------------- INFO ----------------

    def table_size(self, table_name):
        return self._get_table(table_name).size()

    def min_key(self, table_name):
        return self._get_table(table_name).min_key()

    def max_key(self, table_name):
        return self._get_table(table_name).max_key()

    def count(self, table_name):
        return self._get_table(table_name).count_records()
