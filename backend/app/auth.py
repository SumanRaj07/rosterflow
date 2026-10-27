"""Demo-grade token auth: PBKDF2-HMAC password hashing (stdlib, no extra
dependency) and random bearer tokens stored in the DB.

NOTE (documented limitation): this is not production SSO. Tokens are opaque
random values with an expiry; role checks are enforced on every protected
endpoint in the backend, and pod-lead / employee scoping is applied in the
service layer, so frontend tampering alone cannot widen access.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Token, User

TOKEN_TTL_DAYS = 7
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(),
                               200_000).hex()


def new_salt() -> str:
    return secrets.token_hex(16)


def verify_password(password: str, user: User) -> bool:
    return hmac.compare_digest(hash_password(password, user.password_salt),
                               user.password_hash)


def create_token(db: Session, user: User) -> Token:
    tok = Token(user_id=user.id, token=secrets.token_hex(32),
                expires_at=datetime.utcnow() + timedelta(days=TOKEN_TTL_DAYS))
    db.add(tok)
    db.commit()
    db.refresh(tok)
    return tok


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer),
                     db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="Authentication required")
    tok = db.query(Token).filter(Token.token == creds.credentials).first()
    if not tok or tok.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == tok.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    return user


def require_roles(*roles):
    def _check(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


def visible_pod_ids(user: User, db: Session):
    """Pods a user may see. Admins/managers see all; pod leads see their own."""
    from .models import Pod
    if user.role in ("admin", "manager"):
        return None  # all
    if user.role == "pod_lead":
        pods = db.query(Pod).filter(Pod.lead_id == user.id).all()
        return {p.id for p in pods}
    return set()
