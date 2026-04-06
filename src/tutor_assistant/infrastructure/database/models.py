"""SQLAlchemy ORM models."""

from __future__ import annotations

import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("tutor_chat_id", "name", name="uq_student_name_per_tutor"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tutor_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    slots: Mapped[list[ScheduleSlot]] = relationship(
        "ScheduleSlot",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 0=Mon … 6=Sun
    time_start: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=60
    )

    student: Mapped[Student] = relationship("Student", back_populates="slots")


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    daily_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    daily_reminder_time: Mapped[datetime.time | None] = mapped_column(
        Time, nullable=True
    )
    pre_class_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    pre_class_reminder_minutes: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
