import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    token = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Board(Base):
    __tablename__ = "boards"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    cards = relationship("Card", back_populates="board", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True, default=gen_id)
    board_id = Column(String, ForeignKey("boards.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="pendiente")
    assignee_email = Column(String, default="")
    due_date = Column(DateTime, nullable=True)
    attachment_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board", back_populates="cards")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(String, primary_key=True, default=gen_id)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    message = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
