"""Authentication service for user management."""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, ALGORITHM
from app.models import User, UserHistory
from app.schemas import UserRegister, UserLogin, UserHistoryCreate

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def register_user(db: Session, user_data: UserRegister) -> User:
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise ValueError("Username or email already exists")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
    """Authenticate user with username/password."""
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user:
        return None
    if not verify_password(login_data.password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def record_user_history(db: Session, user_id: int, history_data: UserHistoryCreate) -> UserHistory:
    """Record tile analysis for user."""
    db_history = UserHistory(
        user_id=user_id,
        tile_id=history_data.tile_id,
        view_mode=history_data.view_mode
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history


def get_user_history(db: Session, user_id: int, limit: int = 50) -> list[UserHistory]:
    """Get user's tile analysis history."""
    return db.query(UserHistory).filter(
        UserHistory.user_id == user_id
    ).order_by(UserHistory.analyzed_at.desc()).limit(limit).all()
