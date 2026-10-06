from sqlalchemy.orm import Session
from ..models import AuditLog


def log(db: Session, actor_user_id: int | None, action: str, subject_type: str = "", subject_id: int | None = None, **details) -> None:
    db.add(AuditLog(actor_user_id=actor_user_id, action=action, subject_type=subject_type, subject_id=subject_id, details=details))
