import json
import logging
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.models import AuditLog

SENSITIVE_KEYS = ["password", "token", "access_token", "refresh_token", "secret", "key"]

logger = logging.getLogger("security_audit")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('{"ts":"%(asctime)s", "level":"%(levelname)s", "event":%(message)s}'))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False

def get_client_ip(request: Request) -> str:
    """ІР клієнта (враховує X-Forwarded-For від проксі)."""
    if request.headers.get("x-forwarded-for"):
        return request.headers.get("x-forwarded-for").split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def clean(details: dict | None) -> dict | None:
    if not details:
        return None
    return {k: ("***" if k.lower() in SENSITIVE_KEYS else v) for k, v in details.items()}

def log_event(
    db: Session,
    action: str,
    status: str,
    ip_address: str,
    *,
    user_id: int | None = None,
    username: str | None = None,
    http_method: str | None = None,
    endpoint: str | None = None,
    status_code: int | None = None,
    resource: str | None = None,
    details: dict | None = None,
) -> None:
    """Пише подію в audit_log (БД) і в stdout (JSON для docker logs / SIEM)."""
    details = clean(details)
    try:
        db.add(AuditLog(
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            resource=resource,
            http_method=http_method,
            endpoint=endpoint,
            status=status,
            status_code=status_code,
            details=json.dumps(details, ensure_ascii=False) if details else None,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(json.dumps({"action": "audit_write_failed"}))

    level = logging.WARNING if status in ("failure", "warning", "error") else logging.INFO
    logger.log(level, json.dumps({
        "action": action,
        "status": status,
        "user_id": user_id,
        "username": username,
        "ip": ip_address,
        "endpoint": endpoint,
        "code": status_code,
        "details": details,
    }, ensure_ascii=False))

def log_login_success(db: Session, user_id: int, username: str, ip: str) -> None:
    log_event(db, "login_success", "success", ip, user_id=user_id, username=username,
              http_method="POST", endpoint="/auth/login", status_code=200)

def log_login_failed(db: Session, username: str, ip: str, reason: str = "invalid_credentials") -> None:
    log_event(db, "login_failed", "failure", ip, username=username,
              http_method="POST", endpoint="/auth/login", status_code=401,
              details={"reason": reason})

def log_data_change(db: Session, user, ip: str, resource: str, old: dict | None, new: dict | None, endpoint: str | None = None) -> None:
    """Зміна оцінки, ролі тощо (захист від Repudiation)."""
    log_event(db, "data_change", "success", ip, user_id=user.id, username=user.username,
              endpoint=endpoint, resource=resource, details={"old": old, "new": new})
