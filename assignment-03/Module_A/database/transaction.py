from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class TransactionStatus(str, Enum):
    BEGIN = "begin"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionContext:
    operation: str
    table_name: Optional[str] = None
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = TransactionStatus.BEGIN.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    affected_entities: List[Dict[str, Any]] = field(default_factory=list)
    before_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    def activate(self):
        self.status = TransactionStatus.ACTIVE.value

    def commit(self):
        self.status = TransactionStatus.COMMITTED.value

    def mark_failed(self, error_message: str):
        self.status = TransactionStatus.FAILED.value
        self.error_message = error_message

    def rollback(self):
        self.status = TransactionStatus.ROLLED_BACK.value

    def add_affected_entity(self, entity_type: str, entity_name: str, key=None):
        self.affected_entities.append(
            {
                "entity_type": entity_type,
                "entity_name": entity_name,
                "key": key,
            }
        )

    def add_before_snapshot(self, entity_type: str, entity_name: str, key=None, before_value=None):
        self.before_snapshots.append(
            {
                "entity_type": entity_type,
                "entity_name": entity_name,
                "key": key,
                "before_value": before_value,
            }
        )