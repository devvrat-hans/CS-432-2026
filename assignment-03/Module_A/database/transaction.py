from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


# ---------------- STATUS ENUM ----------------
class TransactionStatus(Enum):
    BEGIN = "begin"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


# ---------------- TRANSACTION CONTEXT ----------------
@dataclass
class TransactionContext:
    operation: str
    table_name: Optional[str] = None

    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    status: TransactionStatus = TransactionStatus.BEGIN
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Tracks what is affected (for debugging + observability)
    affected_entities: List[Dict[str, Any]] = field(default_factory=list)

    # Stores BEFORE state (used for rollback + WAL)
    before_snapshots: List[Dict[str, Any]] = field(default_factory=list)

    error_message: Optional[str] = None

    # ---------------- STATE TRANSITIONS ----------------

    def activate(self):
        self.status = TransactionStatus.ACTIVE

    def commit(self):
        self.status = TransactionStatus.COMMITTED

    def rollback(self):
        self.status = TransactionStatus.ROLLED_BACK

    def mark_failed(self, error_message: str):
        self.status = TransactionStatus.FAILED
        self.error_message = error_message

    # ---------------- TRACKING ----------------

    def add_affected_entity(self, entity_type: str, entity_name: str, key=None):
        """
        Track affected table/record (for trace logs & debugging)
        """
        self.affected_entities.append(
            {
                "entity_type": entity_type,   # "table" or "record"
                "entity_name": entity_name,
                "key": key,
            }
        )

    def add_before_snapshot(
        self,
        entity_type: str,
        entity_name: str,
        key=None,
        before_value=None,
    ):
        """
        Store state BEFORE modification (critical for rollback + WAL)
        """
        self.before_snapshots.append(
            {
                "entity_type": entity_type,   # "table" or "record"
                "entity_name": entity_name,
                "key": key,
                "before_value": before_value,
            }
        )

    # ---------------- HELPER METHODS ----------------

    def is_active(self) -> bool:
        return self.status == TransactionStatus.ACTIVE

    def is_committed(self) -> bool:
        return self.status == TransactionStatus.COMMITTED

    def is_failed(self) -> bool:
        return self.status == TransactionStatus.FAILED

    def is_rolled_back(self) -> bool:
        return self.status == TransactionStatus.ROLLED_BACK

    # ---------------- DEBUG ----------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "operation": self.operation,
            "table_name": self.table_name,
            "status": self.status.value,
            "created_at": self.created_at,
            "affected_entities": self.affected_entities,
            "before_snapshots": self.before_snapshots,
            "error_message": self.error_message,
        }

    def __str__(self):
        return (
            f"Transaction("
            f"id={self.transaction_id}, "
            f"status={self.status.value}, "
            f"operation={self.operation}, "
            f"table={self.table_name}"
            f")"
        )