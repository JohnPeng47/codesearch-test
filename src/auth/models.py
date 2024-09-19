from src.config import COWBOY_JWT_ALG, COWBOY_JWT_EXP, COWBOY_JWT_SECRET, ANON_LOGIN
from src.database.core import Base
from src.models import TimeStampMixin, RTFSBase, PrimaryKey
from src.model_relations import user_repo

import random
import string
import secrets
import bcrypt
from jose import jwt
from typing import Optional
from pydantic import validator, Field, BaseModel, root_validator
from pydantic.networks import EmailStr
from sqlalchemy.orm import relationship
from sqlalchemy import (
    ForeignKey,
    DateTime,
    Column,
    String,
    LargeBinary,
    Integer,
    Boolean,
)
from datetime import datetime, timedelta


def generate_token(email):
    now = datetime.utcnow()
    exp = (now + timedelta(seconds=COWBOY_JWT_EXP)).timestamp()
    data = {
        "exp": exp,
        "email": email,
    }
    return jwt.encode(data, COWBOY_JWT_SECRET, algorithm=COWBOY_JWT_ALG)


def generate_password():
    """Generates a reasonable password if none is provided."""
    alphanumeric = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphanumeric) for i in range(10))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)  # noqa
            and sum(c.isdigit() for c in password) >= 3  # noqa
        ):
            break
    return password

def generate_email():
    return "".join([random.choice(string.ascii_letters) for _ in range(10)]) + "@hotmail.com"


def hash_password(password: str):
    """Generates a hashed version of the provided password."""
    pw = bytes(password, "utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt)


class User(Base, TimeStampMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(LargeBinary, nullable=False)
    last_mfa_time = Column(DateTime, nullable=True)
    experimental_features = Column(Boolean, default=False)
    admin = Column(Boolean, default=False)

    repo_user_id = Column(Integer, ForeignKey('repos.id'))
    repos = relationship("Repo", secondary=user_repo, uselist=True, back_populates="users")

    def check_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password)

    @property
    def token(self):
        return generate_token(self.email)


class UserBase(RTFSBase):
    email: Optional[EmailStr]


class UserLogin(UserBase):
    password: str

    @validator("password")
    def password_required(cls, v):
        if not v:
            raise ValueError("Must not be empty string")
        return v


class UserRegister(UserLogin):
    password: Optional[str] = Field(None, nullable=True)

    @root_validator(pre=True)
    def validate_or_anon_auth(cls, values):
        email = values.get("email", None)
        if not ANON_LOGIN and not email:
            raise ValueError("Email must not be empty string")
        if ANON_LOGIN and not email:
            values["email"] = generate_email()
        
        password = values.get("password", None)
        if not password:
            password = generate_password()
        
        values["password"] = hash_password(password)

        return values


# shit doesnt work when returning directly ...
class UserLoginResponse(RTFSBase):
    token: Optional[str] = Field(None, nullable=True) 

class UserRead(UserBase):
    id: PrimaryKey
    role: Optional[str] = Field(None, nullable=True)
    experimental_features: Optional[bool]


class UserUpdate(RTFSBase):
    id: PrimaryKey
    password: Optional[str] = Field(None, nullable=True)

    @validator("password", pre=True)
    def hash(cls, v):
        return hash_password(str(v))


class UserCreate(RTFSBase):
    email: EmailStr
    password: Optional[str] = Field(None, nullable=True)

    @validator("password", pre=True)
    def hash(cls, v):
        return hash_password(str(v))


class UserRegisterResponse(RTFSBase):
    token: Optional[str] = Field(None, nullable=True)


class UpdateOAIKey(BaseModel):
    openai_api_key: str
